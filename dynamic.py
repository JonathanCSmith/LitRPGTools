import copy
import re
import math
from typing import TYPE_CHECKING, Dict, Any, Tuple, List

from data import Entry, Category

if TYPE_CHECKING:
    from data_manager import LitRPGToolsEngine


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
    def __init__(self, engine: 'LitRPGToolsEngine'):
        self.__engine = engine
        self.__value_store: Dict[str, Dict[int, Dict[str, Any]]] = dict()
        self.__function_store: Dict[str, Dict[int, Dict[str, Tuple[str, bool, str]]]] = dict()

        self.__debug = True

    def get_dynamic_data_for_character_id_at_index(self, index: int, character_id: str, private: bool):
        if character_id not in self.__value_store:
            return None
        if index not in self.__value_store[character_id]:
            return None

        # Merge values from our different data stores
        values = self.__value_store[character_id][index]

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

        # Translate
        translated = self.__resolve_dependencies(self.__function_store[character_id][index], self.__value_store[character_id][index], input_string, root_entry_id)

        # Expression check
        return self.__resolve_expressions(translated)

    def __find_special_variables(self, value: str):
        pattern = "!\${([^(}\$!)]*)}\$!"
        return list(set(re.findall(pattern, value)))

    def update(self):
        self.__value_store.clear()
        self.__function_store.clear()

        # Intermediate caches
        character_category_flags = dict()
        rolling_data_cache = dict()
        unevaluated_final_category_data_cache = dict()
        unevaluated_final_entry_data_cache = dict()

        # Loop through entries, skip when not relevant
        characters = self.__engine.get_characters()
        for history_index, entry_id in enumerate(self.__engine.get_history()):

            # Preallocate our caches
            if history_index == 0:
                for character in characters:
                    self.__value_store[character.unique_id] = dict()
                    self.__function_store[character.unique_id] = dict()
                    self.__function_store[character.unique_id][0] = dict()

                    # Caches
                    character_category_flags[character.unique_id] = list()
                    rolling_data_cache[character.unique_id] = dict()
                    unevaluated_final_category_data_cache[character.unique_id] = list()  # Interior will be tuples - done to allow multiple entries editing the same key
                    unevaluated_final_entry_data_cache[character.unique_id] = list()  # Interior will be tuples - done to allow multiple entries editing the same key

            # We always copy our data from before or create a new dict for the final cache
            else:
                for character in characters:
                    self.__function_store[character.unique_id][history_index] = self.__function_store[character.unique_id][history_index - 1].copy()

            # Debugging
            if self.__debug:
                if history_index == 77:
                    print("BREAK")

            # Details relevant for this entry
            entry = self.__engine.get_entry_by_id(entry_id)
            character = self.__engine.get_character_by_id(entry.character_id)
            category = self.__engine.get_category_by_id(entry.category_id)

            # Check to see if the category has been initialised
            if category.unique_id not in character_category_flags[character.unique_id]:
                target_data = dict()

                # We do not extract 'FINAL' type data operations unless it's the final entry in the context of the current history index.
                for key, data in category.dynamic_data_operations.items():
                    if data[1] == "FINAL":
                        unevaluated_final_category_data_cache[character.unique_id].append((key, data))
                    else:
                        target_data[key] = data

                # Calculate
                if len(target_data) != 0:
                    self.__calculate_dynamic_data_operation(
                        self.__function_store[character.unique_id][history_index],
                        rolling_data_cache[character.unique_id],
                        target_data)

                # Cache our category id so we don't repeat
                character_category_flags[character.unique_id].append(category.unique_id)

            # Get the dynamic data from this entry and it's category if it's the first entry in the lineage
            target_data = dict()

            # If we are the root in a lineage, we should be evaluating the category template dynamic data here too (i.e. once per lineage)
            root_entry_id = self.__engine.get_root_entry_id_in_series(entry.unique_id)
            if root_entry_id == entry.unique_id:
                for key, data in category.dynamic_data_operation_templates.items():
                    if data[1] == "FINAL":
                        key = self.__resolve_entry_scoped_pointers(key, root_entry_id)
                        unevaluated_final_entry_data_cache[character.unique_id].append((key, data, root_entry_id))
                    else:
                        target_data[key] = data

            # Extract relevant dynamic data from the actual entry data too
            for key, data in entry.dynamic_data_operations.items():
                if data[1] == "FINAL":
                    key = self.__resolve_entry_scoped_pointers(key, root_entry_id)
                    unevaluated_final_entry_data_cache[character.unique_id].append((key, data, root_entry_id))
                else:
                    target_data[key] = data

            # Calculate our dynamic data operations
            if len(target_data) != 0:
                self.__calculate_dynamic_data_operation(
                    self.__function_store[character.unique_id][history_index],
                    rolling_data_cache[character.unique_id],
                    target_data,
                    root_entry_id)

            # Copy our rolling data ready for final data evaluation
            final_data = copy.deepcopy(rolling_data_cache)

            # Loop through characters - and run all of our 'final' type data evaluations
            for character in characters:

                # each is evaluated separately to prevent overwriting when handing calculate_dynamic_data_operations the target data
                target_data = dict()
                for (key, data) in unevaluated_final_category_data_cache[character.unique_id]:
                    target_data.clear()
                    target_data[key] = data
                    self.__calculate_dynamic_data_operation(
                        self.__function_store[character.unique_id][history_index],
                        final_data[character.unique_id],
                        target_data)

                # Here, we also provide the root_entry context for mutagenic key handling
                target_data = dict()
                for (key, data, root_entry_id) in unevaluated_final_entry_data_cache[character.unique_id]:
                    target_data.clear()
                    target_data[key] = data

                    self.__calculate_dynamic_data_operation(
                        self.__function_store[character.unique_id][history_index],
                        final_data[character.unique_id],
                        target_data,
                        root_entry_id)

                # Save our final data set
                self.__value_store[character.unique_id][history_index] = final_data[character.unique_id]

    def __calculate_dynamic_data_operation(self, functions_cache: dict, current_dynamic_data_store: dict, dynamic_data: Dict[str, Tuple[str, bool, str]], root_entry_id: str = None):
        for dynamic_data_key, (dynamic_data_type, dynamic_data_scope, dynamic_data_operation) in dynamic_data.items():

            # Debug - key check
            if self.__debug:
                if dynamic_data_key == "SPENT_INFLUENCE":
                    print("BREAK")

            # Resolve entry specific scoped dynamic data in the key
            if root_entry_id is not None:
                dynamic_data_key = self.__resolve_entry_scoped_pointers(dynamic_data_key, root_entry_id)

            # Store globals, no need to resolve until referenced
            if dynamic_data_scope == "FUNCTION":
                functions_cache[dynamic_data_key] = (dynamic_data_type, dynamic_data_scope, dynamic_data_operation)
                continue

            # Replace dependencies in the operation string
            # dynamic_data_key = self.__resolve_dependencies(functions_cache, current_dynamic_data_store, final_data_store, dynamic_data_key, root_entry_id)
            dynamic_data_operation = self.__resolve_dependencies(functions_cache, current_dynamic_data_store, dynamic_data_operation, root_entry_id)

            # Apply
            self.__apply_dynamic_data_operation(current_dynamic_data_store, dynamic_data_key, dynamic_data_type, dynamic_data_operation)

    def __resolve_dependencies(self, functions: dict, current_data_store: dict, operation_string: str, root_entry_id: str = None):
        # Resolve special cases
        operation_string = self.__resolve_special_cases(functions, current_data_store, operation_string)

        # Resolve entry specific scoped dynamic data in the operation string
        if root_entry_id is not None:
            operation_string = self.__resolve_entry_scoped_pointers(operation_string, root_entry_id)

        # Identify dependencies and recurse
        dependencies = self.__find_special_variables(operation_string)
        for dependency in dependencies:

            # If our dependency is a function, we resolve now - note functions may still take entry references, so we need that info here
            if dependency in functions:
                value = self.__resolve_function(functions, current_data_store, dependency, root_entry_id)

            # Otherwise check our data store
            elif dependency in current_data_store:
                value = current_data_store[dependency]

            # Meaningful error
            else:
                value = "Could not find dependency: " + dependency + ". Ensure it is initialised before it is referenced."

            # Replace
            operation_string = operation_string.replace("!${" + dependency + "}$!", str(value))

        return operation_string

    def __key_contains_id(self, key: str):
        # pattern = "\$\${ID:([^(}\$\$)]*)}\$\$"
        # regexp = re.compile(pattern)
        # return regexp.search(key)
        return "||ID||:" in key

    def __resolve_entry_scoped_pointers(self, text: str, entry_id: str) -> str:
        return text.replace("$${ID}$$", "||ID||:" + entry_id + "")

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

    def __resolve_function(self, functions: dict, current_data_store: dict, dependency_key: str, root_entry_id: str = None):
        (function_data_type, function_global_flag, function_operation) = functions[dependency_key]
        resolved_value = self.__resolve_dependencies(functions, current_data_store, function_operation, root_entry_id)

        # Function outcomes may need to be evaluated
        try:
            value = eval(resolved_value)
        except Exception as e:
            print("Could not evaluate function outcome for string: " + resolved_value)
            value = resolved_value

        return value

    def __resolve_special_cases(self, functions: dict, current_data_store: dict, text: str, root_entry_id: str = None) -> str:
        pattern = "!\&{([^(}\&!)]*)}\&!"
        expressions = list(set(re.findall(pattern, text)))
        for expression in expressions:
            total = 0

            # Use expression as wildcard search in functions
            for key, val in functions.items():
                if key.endswith(expression):
                    (function_data_type, function_global_flag, function_operation) = functions[key]
                    resolved_value = self.__resolve_dependencies(functions, current_data_store, function_operation, root_entry_id)

                    # Function outcomes may need to be evaluated
                    try:
                        value = eval(resolved_value)
                        total += float(value)
                    except Exception as e:
                        print("Could not evaluate function outcome for string: " + resolved_value)

            # Use expression as wildcard search in current data store
            for key, val in current_data_store.items():
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
