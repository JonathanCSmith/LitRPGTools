import queue
import re
from typing import TYPE_CHECKING, Dict, List, Any

from new.data import Entry, Data

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine


class Operation(Data):
    def __init__(self, key: str, operation_type: str, operation: str, dependencies: List[str]):
        super().__init__()
        self.key = key
        self.operation_type = operation_type
        self.operation = operation
        self.dependencies = dependencies


class DynamicDataStore:
    def __init__(self, engine: 'LitRPGToolsEngine'):
        self.__engine = engine
        self.__value_store: Dict[str, Dict[int, Dict[str, Any]]] = dict()

    def get_dynamic_data_for_character_id_at_index(self, index: int, character_id: str):
        return self.__value_store[character_id][index]

    def translate(self, index: int, character_id: str, input_string: str) -> str:
        keys = self.__find_special_variables(input_string)
        return self.__translate_with_keys_for_entry(index, character_id, input_string, keys)

    def __find_special_variables(self, value: str):
        pattern = "!\${([^(}\$!)]*)}\$!"
        return list(set(re.findall(pattern, value)))

    def update(self):
        self.__value_store.clear()

        # Dynamic data is character specific
        characters = self.__engine.get_characters()

        # Create a dynamic data store
        constant_operations: Dict[str, List[Operation]] = dict()
        for character in characters:
            constant_operations[character.unique_id] = list()

            # Add our 'global' category data
            for category_id in character.categories:
                category = self.__engine.get_category_by_id(category_id)

                # Create and save the operations
                for k, (t, v) in category.dynamic_data_operations.items():
                    dependencies = self.__find_special_variables(v)
                    operation = Operation(k, t, v, dependencies)
                    constant_operations[character.unique_id].append(operation)

        # Loop through entries historically, use to cache dynamic data views?
        history_ids = self.__engine.get_history()
        rolling_window = dict()
        for index, entry_id in enumerate(history_ids):
            entry = self.__engine.get_entry_by_id(entry_id)
            category = self.__engine.get_category_by_id(entry.category_id)

            # Entries are character specific
            character_id = entry.character_id

            # Add in our initial values that are present regardless, and we already have them divvied up by char
            for character in characters:
                if index == 0:
                    self.__value_store[character.unique_id] = dict()
                    rolling_window[character.unique_id] = list()

                # Preallocate our index specific dict
                self.__value_store[character.unique_id][index] = dict()

                # If index != 0 and the current entry isn't about a user, we can just copy the same data from the previous loop
                # This is a 'free' optimisation - don't need to recompute dynamic data per user per entry as an entry can ONLY
                # be linked to one user (implying that for any other user except the one associated with the current entry,
                # the data will remain unchanged)
                if character.unique_id != character_id and index != 0:
                    self.__value_store[character.unique_id][index] = self.__value_store[character.unique_id][index - 1]

            # ALL OPERATIONS BELOW ONLY OCCUR TO THE CHARACTER TIED TO THE ENTRY IN QUESTION IMPLICITLY

            # Preallocate our caches for the 'rolling window' of contextually relevant entries
            operation_targets = list()  # These lists are 'paired' in lieu of a multikey dict/map
            operation_sources = list()
            assign_operation_queue = queue.Queue()
            operation_queue = queue.Queue()

            # Add our constant operations to the queue first
            for operation in constant_operations[character_id]:

                # We need to special case our assignments as we need them to happen before modifications
                # Note, the operations are also initially in the order that they were created, which theoretically reduces
                # The chance of confusion, but is still subject to the vagaries of entries in a series
                if operation.operation_type.startswith("ASSIGN"):
                    assign_operation_queue.put(operation)
                else:
                    operation_queue.put(operation)

                # Store our target
                operation_targets.append(operation.key)
                operation_sources.append(operation.unique_id)

            # Add this latest entry to our rolling window
            rolling_window[character_id].append(entry_id)

            # Now we loop through our rolling window's contents, evaluate if an entry is the most up to date, if not earmark for discarding and continue, otherwise process its dynamic data operations
            to_remove = list()
            for rolling_window_entry_id in rolling_window[character_id]:
                most_current_entry_id = self.__engine.get_most_recent_entry_id_in_series_up_to_index(rolling_window_entry_id, index)

                # There is likely an entry down the line which is more recent so we can skip this and make sure we don't have to look it up again
                if rolling_window_entry_id != most_current_entry_id:
                    to_remove.append(rolling_window_entry_id)
                    continue

                # Get the entry in question
                rolling_window_entry = self.__engine.get_entry_by_id(rolling_window_entry_id)

                # Build a list of our modifications and record dependencies for this entry's category
                for dynamic_data_key, (operation_type, operation_string) in category.dynamic_data_operation_templates.items():
                    # Infer our dependencies, these need to be 'static' in order for us to evaluate the modification
                    dependencies = self.__find_special_variables(operation_string)
                    operation = Operation(dynamic_data_key, operation_type, operation_string, dependencies)

                    # Depending on the type
                    if operation.operation_type.startswith("ASSIGN"):
                        assign_operation_queue.put(operation)
                    else:
                        operation_queue.put(operation)

                    # Store our target
                    operation_targets.append(operation.key)
                    operation_sources.append(operation.unique_id)

                # Build a list of our modifications and record  dependencies for the entry
                for dynamic_data_key, (operation_type, operation_string) in rolling_window_entry.dynamic_data_operations.items():
                    # Infer our dependencies, these need to be 'static' in order for us to evaluate the modification
                    dependencies = self.__find_special_variables(operation_string)
                    operation = Operation(dynamic_data_key, operation_type, operation_string, dependencies)

                    # Depending on the type
                    if operation.operation_type.startswith("ASSIGN"):
                        assign_operation_queue.put(operation)
                    else:
                        operation_queue.put(operation)

                    # Store our target
                    operation_targets.append(operation.key)
                    operation_sources.append(operation.unique_id)

            # Remove the entries no longer pertinent to our rolling window
            for to_remove_entry_id in to_remove:
                rolling_window[character_id].remove(to_remove_entry_id)

            # Process our dual queues such that we prioritise the assignment operations
            # Should no new assignments be applied, defer to the normal operations queue
            # Should a full loop through the remaining queues contents result in no change, bail
            # Note, operations have their dependencies compared to the list of known operation targets
            # In order to maintain a rough dependency chain
            running_ops = True
            while running_ops:

                # Check the assignment queue with a bail clause
                assignments_seen_since_last_ran_op = 0
                while assign_operation_queue.not_empty and assignments_seen_since_last_ran_op != assign_operation_queue.qsize():
                    operation = assign_operation_queue.get()

                    # Check if we can run this operation by comparing the target map to the dependencies
                    if any(dependency in operation_targets for dependency in operation.dependencies):
                        assign_operation_queue.put(operation)
                        assignments_seen_since_last_ran_op += 1
                        continue

                    # No remaining dependencies, run op
                    assignments_seen_since_last_ran_op = 0
                    self.__perform_operation_for_entry_at_index(index, entry, operation)

                    # Remove any target declarations linked to this op
                    map_index = operation_sources.index(operation.unique_id)
                    operation_sources.pop(map_index)
                    operation_targets.pop(map_index)

                # We have run as many assignment operations as we can, now do the same with normals but break on causing a change
                # And then re-evaluate the assignments again
                operations_seen_since_last_ran_op = 0
                while operation_queue.not_empty and operations_seen_since_last_ran_op != operation_queue.qsize():
                    operation = operation_queue.get()

                    # Check if we can run this operation by comparing the target map to the dependencies
                    if any(dependency in operation_targets for dependency in operation.dependencies):
                        assign_operation_queue.put(operation)
                        assignments_seen_since_last_ran_op += 1
                        continue

                    # No missing dependencies, run op
                    operations_seen_since_last_ran_op = 0
                    self.__perform_operation_for_entry_at_index(index, entry, operation)

                    # Remove any target declarations linked to this op
                    map_index = operation_sources.index(operation.unique_id)
                    operation_sources.pop(map_index)
                    operation_targets.pop(map_index)

                    # Force the outer while loop to re-evaluate instead of continuing with the inner (but only if there are remaining assignments)
                    if assign_operation_queue.qsize() > 0:
                        operations_seen_since_last_ran_op = -1  # Acts as a flag for downstream to let the loop logic know that it should re-try one more type
                        break

                # Handle when we have checked everything that we can, then break out of this loop
                if operations_seen_since_last_ran_op != -1 and operations_seen_since_last_ran_op == operation_queue.qsize() and assignments_seen_since_last_ran_op == assign_operation_queue.qsize():
                    running_ops = False

    def __perform_operation_for_entry_at_index(self, index: int, entry: Entry, operation: Operation):
        try:
            # All of our dependencies are theoretically resolved, so now we should evaluate our expression
            operation_string = self.__translate_with_keys_for_entry(index, entry.character_id, operation.operation, operation.dependencies)
            outcome = eval(operation_string)

            # Match by operation type
            match operation.operation_type:
                case "ASSIGN STRING":
                    self.__value_store[entry.character_id][index][operation.key] = outcome

                case "ASSIGN INTEGER":
                    self.__value_store[entry.character_id][index][operation.key] = int(outcome)

                case "ASSIGN FLOAT":
                    self.__value_store[entry.character_id][index][operation.key] = float(outcome)

                case "ADD INTEGER":
                    self.__value_store[entry.character_id][index][operation.key] += int(outcome)

                case "ADD FLOAT":
                    self.__value_store[entry.character_id][index][operation.key] += float(outcome)

                case "SUBTRACT INTEGER":
                    self.__value_store[entry.character_id][index][operation.key] -= int(outcome)

                case "SUBTRACT FLOAT":
                    self.__value_store[entry.character_id][index][operation.key] -= int(outcome)

                case "MULTIPLY INTEGER":
                    self.__value_store[entry.character_id][index][operation.key] *= int(outcome)

                case "MULTIPLY FLOAT":
                    self.__value_store[entry.character_id][index][operation.key] *= float(outcome)

                case "DIVIDE INTEGER":
                    self.__value_store[entry.character_id][index][operation.key] //= int(outcome)

                case "DIVIDE FLOAT":
                    self.__value_store[entry.character_id][index][operation.key] /= float(outcome)

                case _:
                    raise Exception("INVALID OPERATION TYPE")

        except Exception as ex:
            print("Unable to perform operation of key: " + operation.key + " for entry: " + entry.unique_id + " for character: " + entry.character_id + " at index: " + str(index) + " with source operation: " + operation.operation + ". Reported exception was: " + str(ex))

    def __translate_with_keys_for_entry(self, index: int, character_id: str, input_string: str, keys: List[str]) -> str:
        for key in keys:
            if key in self.__value_store[character_id][index]:
                value = self.__value_store[character_id][index][key]
            else:
                value = "COULD NOT FIND VALUE FOR KEY: " + key + " IN DYNAMIC DATA STORE: INITIALISE THE VARIABLE FIRST!"

            input_string = input_string.replace("!${" + key + "}$!", str(value))
        return input_string

    # def update(self):
    #     # Clear our data cache
    #     self.__value_store.clear()
    #
    #     # Get our data stores
    #     characters = self.__engine.get_characters()
    #     categories = self.__engine.get_categories()
    #     entries = list()
    #     root_entry_ids = self.__engine.get_root_entry_ids()
    #     for root_entry_id in root_entry_ids:
    #         current_entry_id = self.__engine.get_most_recent_entry_id_in_series(root_entry_id)
    #         if current_entry_id is not None:
    #             entries.append(self.__engine.get_entry_by_id(current_entry_id))
    #
    #     # All data is character specific (ASSUMPTION!) and can therefore be indexed as such
    #     for character in characters:
    #         character_value_store: Dict[str, str] = dict()
    #         self.__value_store[character.unique_id] = character_value_store
    #
    #     # Initialise our variables. This will then be used as the reference for all variable modifications.
    #     # Variable modifications occuring on undeclared variables will fail and report
    #     self.__initialise_dynamic_data(characters, categories, entries)
    #
    #     # Evaluate all modifications relevant to this state for every character
    #     for character in characters:
    #         self.__evaluate_dynamic_data_modifications(character, categories, entries)
    #
    # def __initialise_dynamic_data(self, characters: List[Character], categories: List[Category], entries: List[Entry]):
    #     # Category specific data
    #     for category in categories:
    #         for dynamic_data_key, initial_value in category.dynamic_data_initialisations.items():
    #             # Loop through the characters, if they have this category, assign the item
    #             for character in characters:
    #                 if category.unique_id in character.categories:
    #                     self.__value_store[character.unique_id][dynamic_data_key] = initial_value
    #
    #     # Entry specific data
    #     for entry in entries:
    #         for dynamic_data_key, initial_value in entry.dynamic_data_initialisations.items():
    #             # Direct assign to character
    #             self.__value_store[entry.character_id][dynamic_data_key] = initial_value
    #
    # def __evaluate_dynamic_data_modifications(self, character: Character, categories: List[Category], entries: List[Entry]):
    #     # Preallocate our caches, index by character because it may be different for each
    #     modification_targets = list()  # These lists are 'paired' in lieu of a multikey dict/map
    #     modification_sources = list()
    #     modifications = queue.Queue()
    #
    #     # Gather our 'modifications' from all sources & convert them into objects for ease of use.
    #     for category in categories:
    #         # Skip if this category doesn't belong to our character
    #         if category.unique_id not in character.categories:
    #             continue
    #
    #         for key, (operation_string, operation_type) in category.dynamic_data_operations.items():
    #             # Infer our dependencies, these need to be 'static' in order for us to evaluate the modification
    #             dependencies = self.__find_special_variables(operation_string)
    #             modification = Modification(key, operation_type, operation_string, dependencies)
    #             modifications.put(modification)
    #
    #             # Store our dependencies
    #             for dependency in dependencies:
    #                 modification_targets.append(dependency)
    #                 modification_sources.append(modification.unique_id)
    #
    #     # Repeat the above for entries
    #     for entry in entries:
    #         # Skip if entry doesn't belong to our character
    #         if entry.character_id != character.unique_id:
    #             continue
    #
    #         for key, (operation_string, operation_type) in entry.dynamic_data_operations.items():
    #             # Infer our dependencies, these need to be 'static' in order for us to evaluate the modification
    #             dependencies = self.__find_special_variables(operation_string)
    #             modification = Modification(key, operation_type, operation_string, dependencies)
    #             modifications.put(modification)
    #
    #             # Store our dependencies
    #             for dependency in dependencies:
    #                 modification_targets.append(dependency)
    #                 modification_sources.append(modification.unique_id)
    #
    #     # Work through our operations, but have an escape for endless loops
    #     modifications_since_last_processed = 0
    #     while modifications.not_empty and modifications_since_last_processed != modifications.qsize():
    #         modification = modifications.get()
    #
    #         # Check through the dependents in the target map, if present, re-add to queue
    #         for dependency in modification.dependencies:
    #             if dependency in modification_targets:
    #                 modifications.put(modification)
    #                 modifications_since_last_processed += 1
    #                 continue
    #
    #         # Reset our counter
    #         modifications_since_last_processed = 0
    #         self.__perform_modification(character, modification)
    #
    #         # Remove our pointers for future modification dependency evaluation
    #         index = modification_sources.index(modification.unique_id)
    #         modification_sources.pop(index)
    #         modification_targets.pop(index)
    #
    # def __perform_modification(self, character: Character, modification: Modification):
    #     try:
    #         # Check if our target key exists
    #         if modification.key not in self.__value_store[character.unique_id]:
    #             raise KeyError(modification.key + " not in dynamic data store when attempting to target for modification.")
    #
    #         # All of our dependencies are theoretically resolved, so now we should evaluate our expression
    #         operation_string = self.__translate_with_keys(character.unique_id, modification.operation, modification.dependencies)
    #         outcome = eval(operation_string, {'__builtins__': None})
    #
    #         # Match by operation type
    #         match modification.operation_type:
    #             case "ASSIGN":
    #                 self.__value_store[character.unique_id][modification.key] = outcome
    #
    #             case "ADD INTEGER":
    #                 self.__value_store[character.unique_id][modification.key] += int(outcome)
    #
    #             case "ADD FLOAT":
    #                 self.__value_store[character.unique_id][modification.key] += float(outcome)
    #
    #             case "SUBTRACT INTEGER":
    #                 self.__value_store[character.unique_id][modification.key] -= int(outcome)
    #
    #             case "SUBTRACT FLOAT":
    #                 self.__value_store[character.unique_id][modification.key] -= int(outcome)
    #
    #             case "MULTIPLY INTEGER":
    #                 self.__value_store[character.unique_id][modification.key] *= int(outcome)
    #
    #             case "MULTIPLY FLOAT":
    #                 self.__value_store[character.unique_id][modification.key] *= float(outcome)
    #
    #             case "DIVIDE INTEGER":
    #                 self.__value_store[character.unique_id][modification.key] //= int(outcome)
    #
    #             case "DIVIDE FLOAT":
    #                 self.__value_store[character.unique_id][modification.key] /= float(outcome)
    #
    #             case _:
    #                 raise Exception("INVALID OPERATION TYPE")
    #
    #     except Exception as ex:
    #         print("Unable to perform modification of key: " + modification.key + "to character: " + character.name + " with source modification: " + modification.operation + ". Reported exception was: " + str(ex))
    #
    # def __translate_with_keys(self, character_id: str, input_string: str, keys: List[str]) -> str:
    #     for key in keys:
    #         if key in self.__value_store[character_id]:
    #             value = self.__value_store[character_id][key]
    #         else:
    #             value = "COULD NOT FIND VALUE FOR KEY: " + key + " IN DYNAMIC DATA STORE: INITIALISE THE VARIABLE FIRST!"
    #
    #         input_string = input_string.replace(key, value)
    #     return input_string