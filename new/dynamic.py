import queue
import re
from typing import TYPE_CHECKING, Dict, List

from new.data import Character, Category, Entry, Data

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine


class Modification(Data):
    def __init__(self, key: str, operation_type: str, operation: str, dependencies: List[str]):
        super().__init__()
        self.key = key
        self.operation_type = operation_type
        self.operation = operation
        self.dependencies = dependencies


class DynamicDataStore:
    def __init__(self, engine: 'LitRPGToolsEngine'):
        self.__engine = engine
        self.__value_store: Dict[str, Dict[str, str]] = dict()

    def translate(self, character_id: str, input_string: str) -> str:
        keys = self.__find_special_variables(input_string)
        return self.__translate_with_keys(character_id, input_string, keys)

    def __find_special_variables(self, value: str):
        pattern = "!\${([^(}\$!)]*)}\$!"
        return re.findall(pattern, value)

    def __translate_with_keys(self, character_id: str, input_string: str, keys: List[str]) -> str:
        for key in keys:
            if key in self.__value_store[character_id]:
                value = self.__value_store[character_id][key]
            else:
                value = "COULD NOT FIND VALUE FOR KEY: " + key + " IN DYNAMIC DATA STORE: INITIALISE THE VARIABLE FIRST!"

            input_string = input_string.replace(key, value)
        return input_string

    def update(self):
        # Clear our data cache
        self.__value_store.clear()
        operations = queue.Queue()
        target_map: Dict[str, List[str]] = dict()

        # Get our data stores
        characters = self.__engine.get_characters()
        categories = self.__engine.get_categories()
        entries = list()
        root_entry_ids = self.__engine.get_root_entry_ids()
        for root_entry_id in root_entry_ids:
            current_entry_id = self.__engine.get_most_recent_entry_id_in_series(root_entry_id)
            if current_entry_id is not None:
                entries.append(self.__engine.get_entry_by_id(current_entry_id))

        # All data is character specific (ASSUMPTION!) and can therefore be indexed as such
        for character in characters:
            character_value_store: Dict[str, str] = dict()
            self.__value_store[character.unique_id] = character_value_store

        # Initialise our variables. This will then be used as the reference for all variable modifications.
        # Variable modifications occuring on undeclared variables will fail and report
        self.__initialise_dynamic_data(characters, categories, entries)

        # Evaluate all modifications relevant to this state for every character
        for character in characters:
            self.__evaluate_dynamic_data_modifications(character, categories, entries)

    def __initialise_dynamic_data(self, characters: List[Character], categories: List[Category], entries: List[Entry]):
        # Category specific data
        for category in categories:
            for dynamic_data_key, initial_value in category.dynamic_data_initialisations.items():
                # Loop through the characters, if they have this category, assign the item
                for character in characters:
                    if category.unique_id in character.categories:
                        self.__value_store[character.unique_id][dynamic_data_key] = initial_value

        # Entry specific data
        for entry in entries:
            for dynamic_data_key, initial_value in entry.dynamic_data_initialisations.items():
                # Direct assign to character
                self.__value_store[entry.character_id][dynamic_data_key] = initial_value

    def __evaluate_dynamic_data_modifications(self, character: Character, categories: List[Category], entries: List[Entry]):
        # Preallocate our caches, index by character because it may be different for each
        modification_targets = list()  # These lists are 'paired' in lieu of a multikey dict/map
        modification_sources = list()
        modifications = queue.Queue()

        # Gather our 'modifications' from all sources & convert them into objects for ease of use.
        for category in categories:
            # Skip if this category doesn't belong to our character
            if category.unique_id not in character.categories:
                continue

            for key, (operation_string, operation_type) in category.dynamic_data_operations.items():
                # Infer our dependencies, these need to be 'static' in order for us to evaluate the modification
                dependencies = self.__find_special_variables(operation_string)
                modification = Modification(key, operation_type, operation_string, dependencies)
                modifications.put(modification)

                # Store our dependencies
                for dependency in dependencies:
                    modification_targets.append(dependency)
                    modification_sources.append(modification.unique_id)

        # Repeat the above for entries
        for entry in entries:
            # Skip if entry doesn't belong to our character
            if entry.character_id != character.unique_id:
                continue

            for key, (operation_string, operation_type) in entry.dynamic_data_operations.items():
                # Infer our dependencies, these need to be 'static' in order for us to evaluate the modification
                dependencies = self.__find_special_variables(operation_string)
                modification = Modification(key, operation_type, operation_string, dependencies)
                modifications.put(modification)

                # Store our dependencies
                for dependency in dependencies:
                    modification_targets.append(dependency)
                    modification_sources.append(modification.unique_id)

        # Work through our operations, but have an escape for endless loops
        modifications_since_last_processed = 0
        while modifications.not_empty and modifications_since_last_processed != modifications.qsize():
            modification = modifications.get()

            # Check through the dependents in the target map, if present, re-add to queue
            for dependency in modification.dependencies:
                if dependency in modification_targets:
                    modifications.put(modification)
                    modifications_since_last_processed += 1
                    continue

            # Reset our counter
            modifications_since_last_processed = 0
            self.__perform_modification(character, modification)

            # Remove our pointers for future modification dependency evaluation
            index = modification_sources.index(modification.unique_id)
            modification_sources.pop(index)
            modification_targets.pop(index)

    def __perform_modification(self, character: Character, modification: Modification):
        try:
            # Check if our target key exists
            if modification.key not in self.__value_store[character.unique_id]:
                raise KeyError(modification.key + " not in dynamic data store when attempting to target for modification.")

            # All of our dependencies are theoretically resolved, so now we should evaluate our expression
            operation_string = self.__translate_with_keys(character.unique_id, modification.operation, modification.dependencies)
            outcome = eval(operation_string, {'__builtins__': None})

            # Match by operation type
            match modification.operation_type:
                case "ASSIGN":
                    self.__value_store[character.unique_id][modification.key] = outcome

                case "ADD INTEGER":
                    self.__value_store[character.unique_id][modification.key] += int(outcome)

                case "ADD FLOAT":
                    self.__value_store[character.unique_id][modification.key] += float(outcome)

                case "SUBTRACT INTEGER":
                    self.__value_store[character.unique_id][modification.key] -= int(outcome)

                case "SUBTRACT FLOAT":
                    self.__value_store[character.unique_id][modification.key] -= int(outcome)

                case "MULTIPLY INTEGER":
                    self.__value_store[character.unique_id][modification.key] *= int(outcome)

                case "MULTIPLY FLOAT":
                    self.__value_store[character.unique_id][modification.key] *= float(outcome)

                case "DIVIDE INTEGER":
                    self.__value_store[character.unique_id][modification.key] //= int(outcome)

                case "DIVIDE FLOAT":
                    self.__value_store[character.unique_id][modification.key] /= float(outcome)

                case _:
                    raise Exception("INVALID OPERATION TYPE")

        except Exception as ex:
            print("Unable to perform modification of key: " + modification.key + "to character: " + character.name + " with source modification: " + modification.operation + ". Reported exception was: " + str(ex))
