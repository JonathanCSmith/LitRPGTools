import copy
import re
from typing import TYPE_CHECKING, Dict, Any, Tuple

if TYPE_CHECKING:
    from data.data_manager import DataManager


class DynamicDataOperation:
    def __init__(self, dynamic_data_key: str, creation_index: int, dynamic_data_type: str, dynamic_data_global_flag: bool, dynamic_data_operation: str):
        self.dynamic_data_key = dynamic_data_key
        self.creation_index = creation_index
        self.dynamic_data_type = dynamic_data_type
        self.dynamic_data_global_flag = dynamic_data_global_flag
        self.dynamic_data_operation = dynamic_data_operation

    def __str__(self):
        return "Operation (" + self.dynamic_data_key + "): " + self.dynamic_data_type + " using string: " + self.dynamic_data_operation

    def __repr__(self):
        return "Operation (" + self.dynamic_data_key + "): " + self.dynamic_data_type + " using string: " + self.dynamic_data_operation


class DynamicDataStore:
    def __init__(self, engine: 'DataManager'):
        self.__engine = engine
        # self.__value_store: Dict[str, Dict[int, Dict[str, Any]]] = dict()
        self.__value_store: Dict[int, Dict[str, Dict[str, Any]]] = dict()
        self.__function_store: Dict[int, Dict[str, Dict[str, Tuple[str, str, str]]]] = dict()

        self.__debug = True

    def get_dynamic_data_for_character_id_at_index(self, index: int, character_id: str, private: bool):
        # Escape if we don't have data here
        if index not in self.__value_store or character_id not in self.__value_store[index]:
            return

        # Merge values from our different data stores
        values = self.__value_store[index][character_id]

        # Return if private values are desired
        if private:
            return values

        # Remove private values if required
        out = dict()
        for key in values.keys():
            if not self.__key_contains_id(key):
                out[key] = values[key]

        return out

    def translate(self, index: int, character_id: str, entry_id: str, input_string: str) -> str:
        # Obtian the root entry id just in case there are entry scoped pointers
        root_entry_id = self.__engine.get_root_entry_id_in_series(entry_id)

        # Inject our reference keys here
        input_string = self.__resolve_id_pointers(input_string, root_entry_id)

        # Translate
        translated = self.__resolve_dependencies(character_id, index, input_string, root_entry_id)

        # Expression check
        return self.__resolve_expressions(translated)

    def update(self):
        self.__value_store.clear()
        self.__function_store.clear()

        # Intermediate caches - these are necessary because different data sets are 'preserved' differnently
        rolling_data_cache = dict()  # This cache 'remembers' all non-final dynamic data operations. It is updated in a 'rolling' type manner as the loop progresses
        unevaluated_final_category_data_cache = dict()  # This is used to cache the category specific dynamic data to apply at the end of a given loop. It is updated in a 'rolling' type manner as the loop progresses.
        unevaluated_final_entry_data_cache = dict()  # This is used to cache the entry specific dynamic data to apply at the end of a given loop. It is updated in a 'rolling' type manner as the loop progresses.

        # Single look up caching
        characters = self.__engine.get_characters()

        # Loop through entries in order
        for history_index, entry_id in enumerate(self.__engine.get_history()):

            # Preallocate our caches
            if history_index == 0:
                self.__value_store[0] = dict()
                self.__function_store[0] = dict()

                # Preallocate for each character
                for character in characters:
                    self.__value_store[0][character.unique_id] = dict()  # We have to preallocate needlessly here so that the lookups this loop don't fail
                    self.__function_store[0][character.unique_id] = dict()

                    # Cache preallocations - see above for reasons
                    rolling_data_cache[character.unique_id] = dict()
                    unevaluated_final_category_data_cache[character.unique_id] = list()  # Interior will be tuples - done to allow multiple entries editing the same key
                    unevaluated_final_entry_data_cache[character.unique_id] = list()  # Interior will be tuples - done to allow multiple entries editing the same key

                    # Initialise our categories so that we ensure that their default dynamic data is available no matter what
                    for category_id in character.categories:
                        category = self.__engine.get_category_by_id(category_id)

                        # Extract the category specific dynamic data
                        for dynamic_data_key, (dynamic_data_type, dynamic_data_scope, dynamic_data_operation) in category.dynamic_data_operations.items():
                            self.__evaluate_dynamic_data_operation(dynamic_data_key, dynamic_data_type, dynamic_data_scope, dynamic_data_operation, character.unique_id, 0, unevaluated_final_category_data_cache, rolling_data_cache)

            # We always copy our data from the previous loop iteration so that it can be used internally within the loop operation
            else:
                # This copy operation is ephemeral and is replaced before we are evaluating this loops final type dynamic data
                # Before this, it is used internally to perform lookups on the previous loop's data without having to handle -1 index edge cases or dual dict reference
                self.__value_store[history_index] = copy.deepcopy(self.__value_store[history_index - 1])

                # Function stores are preserved throughout the loop iterations and built upon
                self.__function_store[history_index] = copy.deepcopy(self.__function_store[history_index - 1])

            # Debugging
            if self.__debug and history_index == 45:
                print("BREAK")

            # Details relevant for this entry
            entry = self.__engine.get_entry_by_id(entry_id)
            character = self.__engine.get_character_by_id(entry.character_id)
            category = self.__engine.get_category_by_id(entry.category_id)

            # If we are the root in a lineage, we should be evaluating the template dynamic data here too (i.e. once per lineage)
            root_entry_id = self.__engine.get_root_entry_id_in_series(entry.unique_id)
            if root_entry_id == entry.unique_id:
                for dynamic_data_key, (dynamic_data_type, dynamic_data_scope, dynamic_data_operation) in category.dynamic_data_operation_templates.items():
                    self.__evaluate_dynamic_data_operation(dynamic_data_key, dynamic_data_type, dynamic_data_scope, dynamic_data_operation, character.unique_id, history_index, unevaluated_final_entry_data_cache, rolling_data_cache, root_entry_id)

            # Extract relevant dynamic data from the actual entry data too
            for dynamic_data_key, (dynamic_data_type, dynamic_data_scope, dynamic_data_operation) in entry.dynamic_data_operations.items():
                self.__evaluate_dynamic_data_operation(dynamic_data_key, dynamic_data_type, dynamic_data_scope, dynamic_data_operation, character.unique_id, history_index, unevaluated_final_entry_data_cache, rolling_data_cache, root_entry_id)

            # Copy our rolling data into our value store ready for the evaluation of this loops final dynamic data
            self.__value_store[history_index] = copy.deepcopy(rolling_data_cache)

            # Loop through characters - and run all of our 'final' type data evaluations
            for character in characters:
                # These are explicitly evaluated first
                for (dynamic_data_key, dynamic_data_type, dynamic_data_scope, dynamic_data_operation, root_entry_id) in unevaluated_final_category_data_cache[character.unique_id]:
                    self.__evaluate_dynamic_data_operation(dynamic_data_key, dynamic_data_type, "INSTANT", dynamic_data_operation, character.unique_id, history_index, None, None)

                # For entry type finals we also provide the root_entry context for mutagenic key handling
                for (dynamic_data_key, dynamic_data_type, dynamic_data_scope, dynamic_data_operation, root_entry_id) in unevaluated_final_entry_data_cache[character.unique_id]:
                    self.__evaluate_dynamic_data_operation(dynamic_data_key, dynamic_data_type, "INSTANT", dynamic_data_operation, character.unique_id, history_index, None, None, root_entry_id)

    def __evaluate_dynamic_data_operation(self, dynamic_data_key: str, dynamic_data_type: str, dynamic_data_scope: str, dynamic_data_operation: str, character_id: str, history_index: int, final_operation_store: dict, operation_results_store: dict, root_entry_id: str = None):
        """

        :param dynamic_data_key:
        :param dynamic_data_type:
        :param dynamic_data_scope:
        :param dynamic_data_operation:
        :param character_id:
        :param history_index:
        :param final_operation_store:
        :param operation_results_store:
        :param root_entry_id:
        :return:
        """
        # Debug - key check
        if self.__debug and "LOYALTY_EFFECTIVE" in dynamic_data_key:
            print("BREAK")

        # Inject our reference keys here
        if root_entry_id is not None:
            dynamic_data_key = self.__resolve_id_pointers(dynamic_data_key, root_entry_id)
            dynamic_data_operation = self.__resolve_id_pointers(dynamic_data_operation, root_entry_id)

        # Resolve any dynamic references in our key
        dynamic_data_key = self.__resolve_dependencies(character_id, history_index, dynamic_data_key, root_entry_id)  # Artificially add tags here to force a single match

        # Check our key data for character redirects
        dynamic_character_pointer_check_results = self.__extract_character_reference(dynamic_data_key)
        if dynamic_character_pointer_check_results is not None:
            dynamic_data_key = dynamic_character_pointer_check_results[0]
            character_id_key = dynamic_character_pointer_check_results[1]
        else:
            character_id_key = character_id

        match dynamic_data_scope:
            case "FINAL":
                final_operation_store[character_id_key].append((dynamic_data_key, dynamic_data_type, dynamic_data_scope, dynamic_data_operation, root_entry_id))

            case "FUNCTION":
                dynamic_data_key = self.__resolve_dependencies(character_id, history_index, dynamic_data_key, root_entry_id)
                self.__function_store[history_index][character_id_key][dynamic_data_key] = (dynamic_data_type, dynamic_data_scope, dynamic_data_operation)

            case "INSTANT":
                # Replace dependencies in the operation string
                dynamic_data_operation = self.__resolve_dependencies(character_id, history_index, dynamic_data_operation, root_entry_id)

                # Apply to both our value stores (one with and one without final values applied).
                self.__apply_dynamic_data_operation(self.__value_store[history_index][character_id_key], dynamic_data_key, dynamic_data_type, dynamic_data_operation)
                if operation_results_store is not None:
                    self.__apply_dynamic_data_operation(operation_results_store[character_id_key], dynamic_data_key, dynamic_data_type, dynamic_data_operation)

    def __resolve_dependencies(self, character_id: str, history_index: int, operation_string: str, root_entry_id: str = None):
        """

        :param character_id:
        :param history_index:
        :param operation_string:
        :param root_entry_id:
        :return:
        """
        # Resolve special cases
        operation_string = self.__resolve_special_cases(character_id, history_index, operation_string)

        # Search for paired matched token bookends in a manner that handles nested tokens
        front_token = "!${"
        back_token = "}$!"
        while True:
            start_token_index = operation_string.rfind(front_token)
            end_token_index = operation_string.find(back_token, start_token_index)

            # Handle unmatched or unfound - escape while loop
            if start_token_index == -1 or end_token_index == -1:
                break

            # Extract our target string
            true_lookup_string = operation_string[start_token_index + len(front_token):end_token_index]

            # Debug
            if self.__debug and true_lookup_string == "LOYALTY_EARNED":
                print("DEBUG")

            # Check if we have a modified character pointer
            out = self.__extract_character_reference(true_lookup_string)
            if out is not None:
                if out[1] not in self.__value_store[0]:
                    return "BAD CHARACTER REFERENCE IN LOOKUP: " + true_lookup_string

                lookup_string = out[0]
                current_character_id = out[1]
            else:
                lookup_string = true_lookup_string
                current_character_id = character_id

            # Perform the lookup in our function store as 1st priority
            if lookup_string in self.__function_store[history_index][current_character_id]:
                target_string = self.__resolve_function(current_character_id, history_index, lookup_string, root_entry_id)

            # Then check our current value store
            elif lookup_string in self.__value_store[history_index][current_character_id]:
                target_string = self.__value_store[history_index][current_character_id][lookup_string]

            else:
                return "Could not find lookup reference for key: " + str(true_lookup_string) + ". Full operation string was: " + str(operation_string).replace("!${", "!|$|{").replace("}$!", "}|$|!")

            # Substitute our lookup from the back
            target_string = str(target_string)
            operation_string = target_string.join(operation_string.rsplit(front_token + true_lookup_string + back_token, 1))

        return operation_string

    def __find_special_variables(self, value: str):
        pattern = "!\${([^(}\$!)]*)}\$!"
        return list(set(re.findall(pattern, value)))

    def __key_contains_id(self, key: str):
        # pattern = "\$\${ID:([^(}\$\$)]*)}\$\$"
        # regexp = re.compile(pattern)
        # return regexp.search(key)
        return "||ID||:" in key

    def __resolve_id_pointers(self, text: str, entry_id: str) -> str:
        text = text.replace("$${ID}$$", "||ID||:" + entry_id + "")

        # Search for paired matched token bookends in a manner that handles nested tokens
        front_token = "$${ID:"
        back_token = ":ID}$$"
        while True:
            start_token_index = text.rfind(front_token)
            end_token_index = text.find(back_token, start_token_index)

            # Handle unmatched or unfound - escape while loop
            if start_token_index == -1 or end_token_index == -1:
                break

            # Extract our target Id
            lookup_string = text[start_token_index + len(front_token):end_token_index]

            # Replace with our reference
            text = text.replace(front_token + lookup_string + back_token, "||ID||:" + lookup_string)

        return text

    def __resolve_rolling_pointers(self, text: str, entry_id: str) -> str:
        return text.replace("$${ROLLING}$$", "||ID||:" + entry_id + "")

    def __extract_character_reference(self, text: str) -> Tuple[str, str] | None:
        # Search for our markers
        front_token = "$${CHAR:"
        back_token = ":CHAR}$$"
        start_token_index = text.rfind(front_token)
        end_token_index = text.find(back_token)

        # No character reference found - this will escape some potential bad eggs and mask them but I don't have a better idea for it RN
        if start_token_index == -1 or end_token_index == -1 or start_token_index >= end_token_index:
            return None

        # Returns
        char_id = text[start_token_index + len(front_token):end_token_index]
        return text.replace(front_token + char_id + back_token, ""), char_id

    def __resolve_expressions(self, text: str):
        pattern = "!\={([^(}\=!)]*)}\=!"
        expressions = list(set(re.findall(pattern, text)))
        for expression in expressions:
            try:
                outcome = eval(expression)
                text = text.replace("!={" + expression + "}=!", str(outcome))
            except:
                # Do not replace
                continue

        return text

    def __resolve_function(self, character_id: str, history_index: int, dependency_key: str, root_entry_id: str = None):
        (function_data_type, function_global_flag, function_operation) = self.__function_store[history_index][character_id][dependency_key]

        # Inject our entry pointer into ROLLING references
        if root_entry_id is not None:
            function_operation = self.__resolve_rolling_pointers(function_operation, root_entry_id)

        # Resolve any lookups in the operation string
        resolved_value = self.__resolve_dependencies(character_id, history_index, function_operation, root_entry_id)

        # Function outcomes may need to be evaluated
        try:
            value = eval(resolved_value)
        except Exception as e:
            print("Could not evaluate function outcome for string: " + resolved_value)
            value = resolved_value

        return value

    def __resolve_special_cases(self, character_id: str, history_index: int, text: str, root_entry_id: str = None) -> str:
        pattern = "!\&{([^(}\&!)]*)}\&!"
        expressions = list(set(re.findall(pattern, text)))
        for expression in expressions:
            total = 0

            # Use expression as wildcard search in functions
            for key, (function_data_type, function_global_flag, function_operation, source_root_entry_id) in self.__function_store[history_index][character_id].items():
                if key.endswith(expression):
                    resolved_value = self.__resolve_dependencies(character_id, history_index, function_operation, root_entry_id)

                    # Function outcomes may need to be evaluated
                    try:
                        value = eval(resolved_value)
                        total += float(value)
                    except Exception as e:
                        print("Could not evaluate function outcome for string: " + resolved_value)

            # Use expression as wildcard search in current data store
            for key, val in self.__value_store[history_index][character_id].items():
                if key.endswith(expression):
                    total += float(val)

            # Output our text
            text = text.replace("!&{" + expression + "}&!", str(total))

        return text

    def __apply_dynamic_data_operation(self, target_data_store: dict, key: str, data_type: str, operation: str):
        try:
            # TODO: Catch likely candidates (e.g. '[string]') and assume we intended it a string literal?
            outcome = eval(operation)

        except Exception as ex:
            print("Unable to eval operation string: " + operation + " for key: " + key)
            outcome = operation

        try:
            # Defaults
            if key not in target_data_store:
                if data_type.endswith("STRING"):
                    target_data_store[key] = ""
                elif data_type.endswith("INTEGER"):
                    target_data_store[key] = 0
                elif data_type.endswith("FLOAT"):
                    target_data_store[key] = 0.0

            # Match by operation type
            match data_type:
                case "ASSIGN STRING": target_data_store[key] = outcome
                case "ASSIGN INTEGER": target_data_store[key] = int(outcome)
                case "ASSIGN FLOAT": target_data_store[key] = float(outcome)
                case "ADD INTEGER": target_data_store[key] += int(outcome)
                case "ADD FLOAT": target_data_store[key] += float(outcome)
                case "SUBTRACT INTEGER": target_data_store[key] -= int(outcome)
                case "SUBTRACT FLOAT": target_data_store[key] -= float(outcome)
                case "MULTIPLY INTEGER": target_data_store[key] *= int(outcome)
                case "MULTIPLY FLOAT": target_data_store[key] *= float(outcome)
                case "DIVIDE INTEGER": target_data_store[key] //= int(outcome)
                case "DIVIDE FLOAT": target_data_store[key] /= float(outcome)
                case _:
                    pass

        except Exception as ex:
            print("Unable to perform operation action for operation: " + str(operation))
