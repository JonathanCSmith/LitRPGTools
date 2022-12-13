import json
import sys
from typing import Dict, List

from PyQt6.QtWidgets import QApplication
from indexed import IndexedOrderedDict

from new import search_helper, utils
from new.data import Character, Entry, Category, Output
from new.dynamic import DynamicDataStore
from new.ui.desktop.gui import LitRPGToolsDesktopGUI


"""
TODO: Dynamic data GUI infrastructure
    Entry:
        Everything
        
TODO: History log text inject category info etc etc
 
TODO: GSheets re-impl, When 'deleting' entries that were previously published, they are 'forgotten' and old references stay around (gsheets). More logical ordering of 'named ranges' for published information - make navigation easier.
TODO: Test all output routes
 
TODO: Test all of 'current selection tab' controls
TODO: Do I need to have so much in the update functions?
TODO: Some sort of sort on entry lists? - not in OUTPUT!
TODO: Validate 'current selection' and 'head' behaviour for all actions
TODO: Selectable text everywhere for better clipboarding
TODO: Better notifications when things go wrong
TODO: Help tooltip for creation & update text special stuff (i.e. any token stuff I add in)

TODO: Replace in search?
TODO: Mobile?
TODO: Bullet Points and Bold?
TODO: Switch to Deltas?
TODO: Versionable Categories?
TODO: Rarity vs. Name???
"""


class LitRPGToolsEngine:
    def __init__(self):
        self.runtime = QApplication(sys.argv)
        self.gui = None

        # Runtime flags
        self.started = False

        # Permanent Data
        self.__history = list()
        self.__outputs: Dict[str, Output] = dict()
        self.__characters = IndexedOrderedDict()
        self.__categories = IndexedOrderedDict()
        self.__entries: Dict[str, Entry] = dict()

        # Ephemeral Cache Data (Volatile)
        self.__character_category_root_entry_cache = dict()  # Character id index -> Category id index -> list of entries (only roots!)
        self.__revision_indices = dict()  # All entries -> revision key (which is actually revision root id but hey-ho)
        self.__revisions = dict()  # revision key (which is actually revision root id) -> ordered list of revisions
        self.__output_indices_to_entries = dict()  # Output key -> entry key (in correct order!)
        self.__output_ids_to_indices = dict()

        # Runtime data
        self.file_save_path = None
        self.__history_index = -1
        self.__value_store = dict()

        # Dynamic data store
        self.__dynamic_data_store = DynamicDataStore(self)

    def start(self):
        self.gui = LitRPGToolsDesktopGUI(self, self.runtime)
        self.started = True

    def run(self):
        if not self.started:
            print("Application has not been started")
            return

        self.gui.show()
        sys.exit(self.runtime.exec())

    def save(self):
        # TODO once we know the file structure better
        pass

    def load(self):
        if self.file_save_path:
            with open(self.file_save_path, "r") as source_file:
                json_data = json.load(source_file)
                if "version" not in json_data:
                    # data = SerializationData.from_json(json_data)
                    # TODO Old version handler
                    return

                elif "version" == "2.0.0":
                    # TODO: New version handler

                    return

    def get_unassigned_gsheets(self):
        return list()

    def load_gsheets_credentials(self, file: str):
        pass

    def output_to_gsheets(self):
        pass

    def get_character_ids(self):
        return self.__characters.keys()

    def get_characters(self) -> List[Character]:
        return self.__characters.values()

    def get_character_by_id(self, character_id: str) -> Character | None:
        if character_id in self.__characters:
            return self.__characters[character_id]
        return None

    def move_character_id_left(self, character_id: str):
        out = utils.move_item_in_indexedordererdict_by(self.__characters, character_id, -1)
        if out is not None:
            self.__characters = out

    def move_character_id_right(self, character_id: str):
        out = utils.move_item_in_indexedordererdict_by(self.__characters, character_id, 1)
        if out is not None:
            self.__characters = out

    def add_character(self, character: Character, rebuild_caches=True):
        if character.unique_id not in self.__characters:
            self.__characters[character.unique_id] = character

            # This is excessive here - we can shortcut if its performance heavy
            if rebuild_caches:
                self.__rebuild_caches()

    def edit_character(self, character: Character, rebuild_caches=True):
        original_character = self.__characters[character.unique_id]

        # Need to special case when a category was disassociated from a character
        for category_id in original_character.categories:
            if category_id not in character.categories:

                # Get the entries that match this character and the deleted category for deletion
                root_entries = self.__character_category_root_entry_cache[character.unique_id][category_id]
                for root_entry_id in root_entries:
                    historic_entries = self.__revisions[root_entry_id]

                    # Loop through our history, ignore dependency resolution as we know we are deleting everything
                    for historic_entry in historic_entries:
                        self.delete_entry(historic_entry, rebuild_caches=False)

        # Now just directly reassign as its safe
        self.__characters[character.unique_id] = character

        # Rebuild caches now
        if rebuild_caches:
            self.__rebuild_caches()

    def delete_character(self, character: Character, rebuild_caches=True):
        original_character = self.__characters[character.unique_id]
        for category_id in original_character.categories:

            # Get the entries that match this character and the deleted category for deletion
            root_entries = self.__character_category_root_entry_cache[character.unique_id][category_id]
            for root_entry_id in root_entries:
                historic_entries = self.__revisions[root_entry_id]

                # Loop through our history, ignore dependency resolution as we know we are deleting everything
                for historic_entry_id in historic_entries:
                    self.delete_entry(historic_entry_id, rebuild_caches=False)

        # Delete and optionally rebuild caches
        del self.__characters[character.unique_id]
        if rebuild_caches:
            self.__rebuild_caches()

    def get_categories(self) -> List[Category]:
        return self.__categories.values()

    def get_categories_for_character_id(self, character_id: str) -> list | None:
        if character_id in self.__character_category_root_entry_cache:
            return self.__character_category_root_entry_cache[character_id].keys()
        return None

    def get_category_by_id(self, category_id: str) -> Category | None:
        if category_id in self.__categories:
            return self.__categories[category_id]
        return None

    def move_category_id_left(self, category_id: str):
        out = utils.move_item_in_indexedordererdict_by(self.__categories, category_id, -1)
        if out is not None:
            self.__categories = out

    def move_category_id_right(self, category_id: str):
        out = utils.move_item_in_indexedordererdict_by(self.__categories, category_id, 1)
        if out is not None:
            self.__categories = out

    def add_category(self, category: Category, rebuild_caches=True):
        if category not in self.__categories:
            self.__categories[category.unique_id] = category

            # This is excessive here - we can shortcut if its performance heavy
            if rebuild_caches:
                self.__rebuild_caches()

    def edit_category(self, category: Category, edit_instructions: dict):
        self.__categories[category.unique_id] = category

        # Loop through all the entries associated with a category and update according to the edit instructions
        for character_id in self.__character_category_root_entry_cache:
            root_entries = self.__character_category_root_entry_cache[character_id][category.unique_id]
            for root_entry_id in root_entries:
                for history_entry_id in self.__revisions[root_entry_id]:
                    entry = self.get_entry_by_id(history_entry_id)

                    # Handle all available instructions in order (ORDER MATTERS)
                    for instruction, location in edit_instructions:
                        if instruction == "INSERT_AT":
                            entry.data.insert(location, "")
                        elif instruction == "DELETE":
                            entry.data.pop(location)
                        elif instruction == "MOVE UP":
                            item = entry.data.pop(location)
                            entry.data.insert(location - 1, item)
                        elif instruction == "MOVE DOWN":
                            item = entry.data.pop(location)
                            entry.data.insert(location + 1, item)

        # Update our dynamic data store
        self.__dynamic_data_store.update()

    def delete_category(self, category: Category, rebuild_caches=True):
        # Get the entries that match this category for deletion
        for character_id in self.__character_category_root_entry_cache:
            character = self.__characters[character_id]
            if character.categories.contains[category.unique_id]:
                character.categories.remove(category.unique_id)

            root_entries = self.__character_category_root_entry_cache[character_id][category.unique_id]
            for root_entry_id in root_entries:
                historic_entries = self.__revisions[root_entry_id]

                # Loop through our history, ignore dependency resolution as we know we are deleting everything
                for historic_entry_id in historic_entries:
                    self.delete_entry(historic_entry_id, rebuild_caches=False)

        # Now just directly reassign as its safe
        del self.__categories[category.unique_id]
        if rebuild_caches:
            self.__rebuild_caches()

    def get_outputs(self):
        return self.__outputs.values()

    def get_output_by_id(self, output_id: str) -> Output | None:
        if output_id in self.__outputs:
            return self.__outputs[output_id]
        return None

    def get_index_of_output_from_id(self, output_id: str) -> int | None:
        if output_id in self.__output_ids_to_indices:
            return self.__output_ids_to_indices[output_id]
        return None

    def get_closest_output_index_up_to_index(self, index: int) -> int:
        try:
            return max(k for k in self.__output_indices_to_entries.keys() if k <= index)
        except ValueError:
            return -1

    def move_output_up_by_id(self, output_id: str, rebuild_caches=True):
        if output_id not in self.__outputs:
            return

        # Bail if its a bad move
        index = self.__output_ids_to_indices[output_id]
        if index == 0:
            return

        # Get the pertinent entries
        old_entry_id = self.__output_indices_to_entries[index]
        old_entry = self.get_entry_by_id(old_entry_id)
        new_entry_id = self.__output_indices_to_entries[index - 1]
        new_entry = self.get_entry_by_id(new_entry_id)

        # Bail if an output pointer already points to the new entry
        if new_entry.output_id is not None:
            return

        # Assign
        new_entry.output_id = old_entry.output_id
        old_entry.output_id = None

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def move_output_down_by_id(self, output_id: str, rebuild_caches=True):
        if output_id not in self.__outputs:
            return

        # Bail if its a bad move
        index = self.__output_ids_to_indices[output_id]
        if index == len(self.__history) - 1:
            return

        # Get the pertinent entries
        old_entry_id = self.__output_indices_to_entries[index]
        old_entry = self.get_entry_by_id(old_entry_id)
        new_entry_id = self.__output_indices_to_entries[index + 1]
        new_entry = self.get_entry_by_id(new_entry_id)

        # Bail if an output pointer already points to the new entry
        if new_entry.output_id is not None:
            return

        # Assign
        new_entry.output_id = old_entry.output_id
        old_entry.output_id = None

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def add_output_to_head(self, output: Output, rebuild_caches=True):
        if output.unique_id in self.__outputs:
            return

        entry = self.get_entry_by_id(self.get_most_recent_entry_id())
        if entry.output_id is not None:
            return

        # Assign the data
        self.__outputs[output.unique_id] = output
        entry.output_id = output.unique_id

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def delete_output(self, output: Output, rebuild_caches=True):
        if output.unique_id not in self.__outputs:
            return

        del self.__outputs[output.unique_id]

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def get_entry_by_id(self, entry_id: str) -> Entry | None:
        if entry_id in self.__entries:
            return self.__entries[entry_id]
        return None

    def get_entry_revisions_for_id(self, entry_id: str) -> list[str]:
        revision_id = self.__revision_indices[entry_id]
        return self.__revisions[revision_id]

    def get_most_recent_entry_id(self):
        return self.__history[self.get_current_history_index()]

    def get_most_recent_entry_id_in_series(self, entry_id: str):
        return self.get_most_recent_entry_id_in_series_up_to_index(entry_id, self.get_current_history_index())

    def get_most_recent_entry_id_in_series_up_to_index(self, entry_id: str, index: int) -> str | None:
        if entry_id not in self.__entries:
            return None

        revisions = self.get_entry_revisions_for_id(entry_id)
        if revisions is None:
            print("Badly formed revisions? Need to rebuild caches somewhere?")
            return None

        indices = dict()
        for entry_id in revisions:
            indices[self.__history.index(entry_id)] = entry_id

        try:
            target_index = max(k for k in indices.keys() if k <= index)
            return indices[target_index]
        except ValueError:
            return None

    def get_entry_id_by_history_index(self, index: int) -> str | None:
        if 0 <= index < len(self.__history):
            return self.__history[index]
        return None

    def get_entries_for_character_and_category_at_current_history_index(self, character_id: str, category_id: str) -> list | None:
        if character_id not in self.__character_category_root_entry_cache or category_id not in self.__character_category_root_entry_cache[character_id]:
            print("This really shouldn't happen.")
            return None

        # Get our root entries
        root_entries = self.__character_category_root_entry_cache[character_id][category_id]
        valid_entries = []
        for root_entry in root_entries:
            revisions = self.__revisions[root_entry]

            # Loop through all our revisions
            matching_revision = None
            for revision_id in revisions:
                index = self.get_entry_index_in_history(revision_id)

                # Check their index is less than or equal to the current head
                if index <= self.get_current_history_index():
                    matching_revision = revision_id
                else:
                    break

            # Store if valid
            if matching_revision is not None:
                valid_entries.append(matching_revision)

        return valid_entries

    def get_root_entry_ids(self):
        return self.__revisions.keys()

    def add_entry_at_head(self, entry: Entry, rebuild_caches=True):
        self.__add_entry_at(entry, self.get_current_history_index() + 1, rebuild_caches=rebuild_caches)

    def __add_entry_at(self, entry: Entry, index: int, rebuild_caches=True):
        if entry.unique_id not in self.__entries:
            self.__entries[entry.unique_id] = entry

            # Update parents and children - we assume that what we are given is correct!
            if entry.parent_id is not None:
                parent_entry = self.get_entry_by_id(entry.parent_id)
                parent_entry.child_id = entry.unique_id
            if entry.child_id is not None:
                child_entry = self.get_entry_by_id(entry.child_id)
                child_entry.parent_id = entry.unique_id

            # Update history which will also trigger a cache recalculation
            self.__add_to_history(entry.unique_id, index, rebuild_caches=rebuild_caches)

    def edit_entry(self, entry: Entry):
        if entry.unique_id not in self.__entries:
            return

        # Typically this would actually be the same entry as most operations in place edit the entry, but just in case
        self.__entries[entry.unique_id] = entry

        # Update our dynamic data store - the real reason this function exists
        self.__dynamic_data_store.update()

    def move_entry_to(self, entry: Entry, index: int, rebuild_caches=True):
        if entry.parent_id is None and entry.child_id is None:
            self.__move_in_history(entry.unique_id, index, rebuild_caches=rebuild_caches)
            return

        current_index = self.get_entry_index_in_history(entry.unique_id)
        if current_index == index:
            return

        # Need to check if our parent becomes our child
        if index < current_index and entry.parent_id is not None:
            old_parent_index = self.get_entry_index_in_history(entry.parent_id)

            # Only continue if we are actually moving above our parent or into their space
            if index <= old_parent_index:
                old_parent = self.get_entry_by_id(entry.parent_id)

                # Reassign
                entry.parent_id = old_parent.parent_id
                old_parent.parent_id = entry.unique_id
                old_parent.child_id = entry.child_id
                entry.child_id = old_parent.unique_id

                # Also when appropriate, ensure our second degree relatives are notified
                if entry.parent_id is not None:
                    grand_parent = self.get_entry_by_id(entry.parent_id)
                    grand_parent.child_id = entry.unique_id
                if old_parent.child_id is not None:
                    child = self.get_entry_by_id(old_parent.child_id)
                    child.parent_id = old_parent.unique_id

        # Need to check if our child becomes our parent
        if index > current_index and entry.child_id is not None:
            old_child_index = self.get_entry_index_in_history(entry.child_id)

            # Only continue if we are actually moving below our child
            if index > old_child_index:
                old_child = self.get_entry_by_id(entry.child_id)

                # Reassign
                old_child.parent_id = entry.parent_id
                entry.parent_id = old_child.unique_id
                entry.child_id = old_child.child_id
                old_child.child_id = entry.unique_id

                # Also when appropriate, ensure our second degree relatives are notified
                if old_child.parent_id is not None:
                    grand_parent = self.get_entry_by_id(old_child.parent_id)
                    grand_parent.child_id = old_child.unique_id
                if entry.child_id is not None:
                    child = self.get_entry_by_id(entry.child_id)
                    child.parent_id = entry.unique_id

        # Insert our change into history
        self.__move_in_history(entry.unique_id, index, rebuild_caches=rebuild_caches)

    def delete_entry_and_series(self, entry: Entry, rebuild_caches=True):
        root_id = self.__revision_indices[entry.unique_id]
        revisions = self.__revisions[root_id]

        # Delete working backwards with no cache rebuild until the end
        for entry_id in reversed(revisions):
            entry = self.get_entry_by_id(entry_id)
            self.delete_entry(entry, rebuild_caches=False)

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def delete_entry(self, entry: Entry, rebuild_caches=True):
        entry = self.get_entry_by_id(entry.unique_id)

        # Handle dependency reordering - we assume that what we are given is correct!
        parent_entry = self.get_entry_by_id(entry.parent_id)
        child_entry = self.get_entry_by_id(entry.child_id)
        if parent_entry is not None and child_entry is not None:  # Have parent and child
            parent_entry.child_id = child_entry.unique_id
            child_entry.parent_id = parent_entry.unique_id
        elif parent_entry is not None:  # Have only a parent
            parent_entry.child = None
        elif child_entry is not None:  # Have only a child
            child_entry.parent_id = None

        # Handle if we have an output tagged to this entry
        if entry.output_id is not None:
            current_index = self.__history.index(entry.unique_id)
            output = self.get_output_by_id(entry.output_id)

            # If out entry is pos 0 in history, it's safe to destroy
            if current_index == 0:
                target_index = 1  # This is essentially saying target the NEW zero, when it becomes appropriate, theoretically we should just delete here as 1 long outputs aren't really worth holding on to
            else:
                target_index = current_index - 1

            # Get our target information
            target_entry_id = self.__history[target_index]
            target_entry = self.get_entry_by_id(target_entry_id)

            # If our target entry has an output, delete as working out where shit should go is broken.
            if target_entry.output_id is not None:
                self.delete_output(output, rebuild_caches=False)  # Theoretically we could retry for the current_index + 1 position but 1 long outputs aren't valuable enough to work out the logic
            else:
                target_entry.output_id = entry.output_id

        # Handle deletion of entry
        del self.__entries[entry.unique_id]
        self.__delete_from_history(entry.unique_id, rebuild_caches=rebuild_caches)

    def get_current_history_index(self) -> int:
        return self.__history_index

    def get_entry_index_in_history(self, entry_id: str) -> int | None:
        if entry_id in self.__history:
            return self.__history.index(entry_id)
        return None

    def get_length_of_history(self) -> int:
        return len(self.__history)

    def set_current_history_index(self, index, rebuild_caches=True):
        if index < -1:
            index = -1
        elif index >= len(self.__entries) - 1:
            index = len(self.__entries) - 1

        self.__history_index = index
        if rebuild_caches:
            self.__rebuild_caches()

    def get_history(self):
        return tuple(self.__history.copy())

    def __add_to_history(self, entry_id: str, index=None, rebuild_caches=True):
        if index is None:
            index = self.__history_index + 1

        # Insert entry at +1 from head
        self.__history.insert(index, entry_id)

        # Handle where our head pointer goes - we only need to change when our point of insertion is equal to or above the current head (visually according to list entries)
        if index <= self.__history_index + 1:
            self.set_current_history_index(index, rebuild_caches=rebuild_caches)
        elif rebuild_caches:
            self.__rebuild_caches()

    def __move_in_history(self, entry_id: str, target_index: int, rebuild_caches=True):
        self.__delete_from_history(entry_id, rebuild_caches=False)
        self.__add_to_history(entry_id, target_index, rebuild_caches=rebuild_caches)

    def __delete_from_history(self, entry_id: str, rebuild_caches=True):
        current_index = self.__history.index(entry_id)
        self.__history.remove(entry_id)

        # Handle where our head pointer goes - we only need to change when our point of insertion is equal to or above the current head (visually according to list entries)
        if current_index <= self.__history_index:
            self.set_current_history_index(self.__history_index - 1, rebuild_caches=rebuild_caches)

    def __rebuild_caches(self):
        self.__revision_indices.clear()
        self.__revisions.clear()
        self.__character_category_root_entry_cache.clear()
        self.__output_indices_to_entries.clear()
        self.__output_ids_to_indices.clear()

        # Fix up our character category root cache
        for character_id in self.__characters.keys():
            self.__character_category_root_entry_cache[character_id] = dict()
            character = self.get_character_by_id(character_id)
            for category_id in character.categories:
                self.__character_category_root_entry_cache[character_id][category_id] = []

        # Bail if there's nothing to do - this fixes an odd bug where the history index == 0 but there is nothing... it shouldn't happen if the code was perfect
        if len(self.__history) == 0:
            return

        # Loop through our entries and initialise our entry revision trackers
        for i in range(len(self.__history)):
            unique_key = self.__history[i]
            entry = self.get_entry_by_id(unique_key)

            # We are in a unique situation where we should be working from the root -> leaf for ALL entries, therefore we can make some assumptions (as long as keys are unique!!!)
            if unique_key not in self.__revision_indices:
                self.__revision_indices[unique_key] = unique_key
                revisions_list = [unique_key]

                # Loop through our revisions
                while entry.child_id is not None:
                    self.__revision_indices[entry.child_id] = unique_key
                    revisions_list.append(entry.child_id)
                    entry = self.get_entry_by_id(entry.child_id)

                # Store revisions
                self.__revisions[unique_key] = revisions_list

                # Cache our knowledge regarding an entry's character and category so we don't have to look for them
                self.__character_category_root_entry_cache[entry.character_id][entry.category_id].append(unique_key)

            # Handle outputs
            if entry.output_id is not None:
                self.__output_ids_to_indices[entry.output_id] = i
                self.__output_indices_to_entries[i] = entry.unique_id

                # Rebuild output contents
                output = self.__outputs[entry.output_id]
                lower_limit = self.get_closest_output_index_up_to_index(i) + 1
                truth = list()
                for i2 in reversed(range(lower_limit, i + 1)):
                    output_member_id = self.__history[i2]
                    truth.append(output_member_id)

                    # If we weren't aware of it, store it in ignored
                    if output_member_id not in output.members and output_member_id not in output.ignored:
                        output.ignored.append(output_member_id)

                # Now check for things that we 'remember' but do not exist anymore
                to_remove = list()
                for memory_id in output.members:
                    if memory_id not in truth:
                        to_remove.append(memory_id)
                for memory_id in to_remove:
                    output.members.remove(memory_id)

                to_remove.clear()
                for memory_id in output.ignored:
                    if memory_id not in truth:
                        to_remove.append(memory_id)
                for memory_id in to_remove:
                    output.ignored.remove(memory_id)

        # Dynamic data store
        self.__dynamic_data_store.update()

    def search_all(self, search_string: str) -> list:
        results = []

        # Tokenise our search string
        search_tokens = search_helper.tokenize_string(search_string)
        if search_tokens is None or len(search_tokens) == 0:
            return results

        # Search in entries
        for entry in self.__entries.values():
            entry_tokens = search_helper.tokenize_entry(entry)
            if entry_tokens is None or len(entry_tokens) == 0:
                continue

            if search_helper.search_tokens(search_tokens, entry_tokens):
                results.append(entry)

        # Search in categories
        for category in self.__categories.values():
            category_tokens = search_helper.tokenize_category(category)
            if category_tokens is None or len(search_tokens) == 0:
                continue

            if search_helper.search_tokens(search_tokens, category_tokens):
                results.append(category)

        return results


if __name__ == '__main__':
    # Core
    main = LitRPGToolsEngine()

    # Trigger variable initialization
    main.start()

    # Run the console interaction
    main.run()
