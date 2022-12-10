import json
import sys
from collections import OrderedDict
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFileDialog, QProgressDialog
from indexed import IndexedOrderedDict

from data.categories import Category
from data.data_holder import SerializationData
from data.entries import Entry
from data.tags import Tag
from gui.core_gui import MainGUI
from utils.gsheets import build_gsheets_communicator, SystemSheetLayoutHandler, HistorySheetLayoutHandler


class LitRPGTools:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.gui = None

        # Data holders
        self.__history_index = -1
        self.history = list()
        self.entries = dict()
        self.characters = IndexedOrderedDict()
        self.categories = OrderedDict()
        self.gsheets_credentials_path = None
        self.tags = dict()

        # Caches
        self.entries_for_character_category = dict()  # Character -> Category -> List of latest entries.
        self.entry_revisions = dict()  # Absolute Parent -> Ordered List of Children for Entities
        self.child_to_parent_map = dict()  # Child -> Parent Cache for Entries

        # Subcomponents
        self.gsheets_connector = None
        self.session_path = None

        # Unused but it's a nice template
        self.__character_sheet_template = None
        self.__components = dict()

    def start(self):
        self.gui = MainGUI(self, self.app)

    def run(self):
        self.gui.show()
        sys.exit(self.app.exec())

    def add_character(self, nickname):
        self.characters[nickname] = list()

    def get_character_by_index(self, index):
        return self.characters[self.characters.keys()[index]]

    def get_character_categories(self, name: str) -> list:
        return self.characters[name]

    def get_characters(self):
        return self.characters

    def assign_categories_to_character(self, character: str, categories: list) -> None:
        # Re-order input list such that it maintains our known order
        new_list = []
        for entry in self.characters[character]:
            if entry in categories:
                new_list.append(entry)
            categories.remove(entry)
        new_list.extend(categories)

        self.characters[character] = new_list

    def delete_character(self, character):
        del self.characters[character]

        # Maintain cache coherence
        if character in self.entries_for_character_category:
            character_categories = self.entries_for_character_category[character]
            for category in character_categories:
                entries = character_categories[category]
                for entry in entries:
                    index = self.history.index(entry)
                    self.delete_entry_at_index(index)
            del self.entries_for_character_category[character]

    def delete_character_by_index(self, index):
        del self.characters[self.characters.keys()[index]]

    def get_category(self, category_name: str) -> Category:
        return self.categories[category_name]

    def get_categories(self):
        return self.categories

    def set_categories(self, categories: OrderedDict):
        self.categories = categories

    def add_category(self, category: Category):
        self.categories[category.get_name()] = category

    def edit_category(self, category_name, category: Category):
        if category_name not in self.categories:
            return

        # Try and maintain our order
        if category_name != category.get_name():
            new_categories = OrderedDict()
            for category_key, value in self.categories.items():
                if category_key != category_name:
                    new_categories[category_key] = value
                else:
                    new_categories[category.get_name()] = category

            self.categories = new_categories

        else:
            self.categories[category.get_name()] = category

        # Change all entries
        if category_name != category.get_name():
            for entry in self.entries.values():
                if entry.get_category() == category_name:
                    entry.category = category.get_name()

        self.build_entry_history_caches()

    def delete_category(self, category_name: str):
        if category_name in self.categories:
            del self.categories[category_name]

            # Delete to maintain cache coherence
            for categories_per_character in self.entries_for_character_category.values():
                if category_name in categories_per_character:
                    entries = categories_per_character[category_name]
                    for entry in entries:
                        index = self.history.index(entry)
                        self.delete_entry_at_index(index)

                    del categories_per_character[category_name]

    def get_category_state_for_entity(self, category: str, entity):
        if isinstance(entity, str):
            entity = self.characters.keys().index(entity)

        if entity not in self.entries_for_character_category or category not in self.entries_for_character_category[entity]:
            return None

        return self.entries_for_character_category[entity][category]

    def get_category_state_for_entity_at_time(self, category: str, entity: int, time: int):
        if time == self.get_history_index():
            return self.get_category_state_for_entity(category, entity)

        stored_location = self.get_history_index()
        self.set_current_history_index(time)
        outputs = self.get_category_state_for_entity(category, entity)
        self.set_current_history_index(stored_location)
        return outputs

    def get_entry(self, unique_key) -> Entry:
        return self.entries[unique_key]

    def get_current_entry(self) -> Entry:
        unique_key = self.history[self.__history_index]
        return self.entries[unique_key]

    def get_entry_by_index(self, index) -> Optional[Entry]:
        try:
            unique_key = self.history[index]
        except IndexError:
            return None
        return self.entries[unique_key]

    def get_history_index_from_entry(self, unique_key: str):
        return self.history.index(unique_key)

    def get_entry_key_by_index(self, index):
        return self.history[index]

    def add_entry(self, entry: Entry):
        self.entries[entry.unique_key] = entry

        # Handle linkage insertion
        child_keys = list(self.child_to_parent_map.keys())
        parent_keys = list(self.child_to_parent_map.values())
        if entry.parent_key in parent_keys:  # It may not be if our parent previously didn't have a child
            child_key_to_change = child_keys[parent_keys.index(entry.parent_key)]
            self.child_to_parent_map[child_key_to_change] = entry.unique_key
            target_entry = self.get_entry(child_key_to_change)
            target_entry.parent_key = entry.unique_key

        # Mark our parent as our parent
        if entry.parent_key:
            self.child_to_parent_map[entry.unique_key] = entry.parent_key

        # Add the data to our history
        self.history.insert(self.__history_index + 1, entry.unique_key)
        self.set_current_history_index(self.__history_index + 1)

    def update_existing_entry_values(self, unique_key: str, values: list, should_print_to_overview=None, should_print_to_history=None):
        entry = self.entries[unique_key]
        entry.set_values(values)
        if should_print_to_overview is not None:
            entry.set_print_to_overview(should_print_to_overview)
        if should_print_to_history is not None:
            entry.print_to_history = should_print_to_history

    def delete_entry_at_index(self, index):
        # Remove the entry from our history list
        unique_id = self.history.pop(index)
        del self.entries[unique_id]

        # Handle linkage deletion (i.e. when a link in the entry history log is removed)
        parent_key = None
        if unique_id in self.child_to_parent_map:
            parent_key = self.child_to_parent_map.pop(unique_id)
        values = list(self.child_to_parent_map.values())
        if unique_id in values:
            target_to_change = list(self.child_to_parent_map.keys())[values.index(unique_id)]
            self.child_to_parent_map[target_to_change] = parent_key
            entry = self.get_entry(target_to_change)
            entry.parent_key = parent_key

        # Handle the edge case where we were deleting an item before what we have 'selected'
        if index <= self.__history_index:
            self.set_current_history_index(self.__history_index - 1)

        # Rebuild cache
        self.build_entry_history_caches()

    def get_entry_parent_key(self, unique_key: str):
        if unique_key in self.child_to_parent_map:
            return self.child_to_parent_map[unique_key]
        return None

    def get_child_key_from_parent_key(self, parent_key: str):
        children = list(self.child_to_parent_map.keys())
        parents = list(self.child_to_parent_map.values())
        if parent_key not in parents:
            return None
        return children[parents.index(parent_key)]

    def get_absolute_parent(self, unique_key: str):
        parent_key = None
        key = unique_key
        while True:
            key = self.get_entry_parent_key(key)
            if key is None:
                break
            else:
                parent_key = key

        return parent_key

    def get_most_recent_revision_for_root_entry_key(self, unique_str: str):
        if unique_str in self.entry_revisions:
            return self.entry_revisions[unique_str][-1]
        return None

    def get_all_revisions_for_root_entry_key(self, root_key: str):
        if root_key in self.entry_revisions:
            return self.entry_revisions[root_key]
        return None

    def move_entry_in_history(self, original_location, up):
        original_entry = self.get_entry(self.history[original_location])

        if up:
            new_location = original_location - 1
            displaced_entry = self.get_entry(self.history[new_location])

            # Check if new_location is our parent
            if original_entry.get_parent_key() == displaced_entry.unique_key:
                hold = displaced_entry.unique_key
                displaced_entry.parent_key = original_entry.get_parent_key()
                original_entry.parent_key = hold

        else:
            new_location = original_location + 1
            displaced_entry = self.get_entry(self.history[new_location])

            # Check if new_location is our child
            if displaced_entry.get_parent_key() == original_entry.unique_key:
                hold = original_entry.unique_key
                original_entry.parent_key = displaced_entry.get_parent_key()
                displaced_entry.parent_key = hold

        # Swap!
        self.history[original_location], self.history[new_location] = self.history[new_location], self.history[original_location]

        # Scaffolds
        self.build_entry_history_caches()

    def get_all_category_entries(self, category_name):
        applicable_entries = []
        for entry in self.entries.values():
            if entry.get_category() == category_name:
                applicable_entries.append(entry)

        return applicable_entries

    def build_entry_history_caches(self):
        self.entry_revisions.clear()
        if len(self.history) == 0:
            return

        # Loop through our entries and initialise our entry history trackers as well as build the dynamic data cache
        for i in range(self.get_history_index() + 1):
            unique_key = self.history[i]

            # Rebuild our entry revision information
            parent_key = self.get_absolute_parent(unique_key)
            if parent_key is None:
                self.entry_revisions[unique_key] = [unique_key]
            else:
                self.entry_revisions[parent_key].append(unique_key)

        # Rebuild our category pointers
        self.entries_for_character_category.clear()
        for root_key in self.entry_revisions.keys():
            root_entry = self.get_entry(root_key)
            if root_entry.character not in self.entries_for_character_category:
                self.entries_for_character_category[root_entry.character] = dict()
            if root_entry.category not in self.entries_for_character_category[root_entry.character]:
                self.entries_for_character_category[root_entry.character][root_entry.category] = []
            self.entries_for_character_category[root_entry.character][root_entry.category].append(self.entry_revisions[root_key][-1])

    def get_history(self):
        return self.history

    def get_history_index(self):
        return self.__history_index

    def set_current_history_index(self, index):
        if index < -1:
            index = -1
        elif index >= len(self.entries) - 1:
            index = len(self.entries) - 1

        self.__history_index = index
        self.build_entry_history_caches()

    def add_tag(self, entry_key, tag_name, tag_target):
        self.tags[entry_key] = Tag(tag_name, entry_key, tag_target)

    def get_tag(self, entry_key) -> Optional[Tag]:
        if entry_key in self.tags:
            return self.tags[entry_key]
        return None

    def get_tags(self):
        return self.tags

    def delete_tag(self, entry_key):
        if entry_key in self.tags:
            del self.tags[entry_key]

    def save_as(self):
        file = QFileDialog.getSaveFileName(self.gui, "Save File", "*.litrpg", filter="*.litrpg")
        if file[0] == "":
            return
        self.session_path = file[0]
        self.save()

    def save(self):
        if self.session_path is None:
            return self.save_as()

        # Sort entries with an order - just helps debugging save data
        indices = {v: i for i, v in enumerate(self.history)}
        entries = dict(sorted(self.entries.items(), key=lambda pair: indices[pair[0]]))

        # Save
        data_holder = SerializationData(self.gsheets_credentials_path, self.tags, self.characters, self.categories, self.history, self.__history_index, entries)
        jsons = json.dumps(data_holder, default=lambda o: o.__dict__, indent=4)
        with open(self.session_path, "w") as json_file:
            json_file.write(jsons)

    def load(self):
        file = QFileDialog.getOpenFileName(self.gui, 'OpenFile', filter="*.litrpg")
        if file[0] == "":
            return
        self.session_path = file[0]

        # Load
        with open(self.session_path, "r") as json_file:
            data = json.load(json_file)
            if "__class__" in data:
                raise KeyError

            data_holder = SerializationData.from_json(data)
            self.characters = data_holder.characters
            self.categories = data_holder.categories
            self.history = data_holder.history
            self.entries = data_holder.members
            self.gsheets_credentials_path = data_holder.credentials
            self.tags = data_holder.tags
            history_index = data_holder.history_index

        # Rebuild parent entries
        self.child_to_parent_map = dict()
        for key, entry in self.entries.items():
            parent_key = entry.get_parent_key()
            if key in self.child_to_parent_map:
                raise KeyError("Should not have duplicate child keys in child -> parent map. Bad DAG.")

            if parent_key is not None:
                self.child_to_parent_map[key] = parent_key
        self.set_current_history_index(history_index)

        # Validate parent entries as best as we can - can be used to indicate some mess ups in linkage / manual editing
        parents = list(self.child_to_parent_map.values())
        if len(parents) != len(set(parents)):
            raise ValueError("Should not have duplicate parent keys in child -> parent map. Bad DAG.")

        # Rebuild gsheets connection if appropriate
        if self.gsheets_credentials_path is not None:
            self.gsheets_connector = build_gsheets_communicator(file_path=self.gsheets_credentials_path)
            # self.gsheets_connector.set_batch_mode(True)

        self.gui.handle_update()

    def load_gsheets_credentials(self):
        file = QFileDialog.getOpenFileName(self.gui, 'OpenFile', filter="*.json")
        if file[0] == "":
            return

        self.gsheets_credentials_path = file[0]
        self.gsheets_connector = build_gsheets_communicator(file_path=file[0])

    def get_available_sheets(self):
        try:
            if self.gsheets_connector is not None:
                return self.gsheets_connector.spreadsheet_titles()
            else:
                return list()

        # Sometimes our connection times out
        except ConnectionAbortedError:
            self.gsheets_connector = build_gsheets_communicator(file_path=self.gsheets_credentials_path)
            return self.gsheets_connector.spreadsheet_titles()

    def dump(self):
        # Save beforehand as the api has a way of randomly erroring
        self.save()

        # Rough prediction for user inform (worst case)
        current_count = 0
        worst_case_scenario = len(self.tags) * len(self.categories) * (2 * len(self.characters)) + 1
        progress_bar = QProgressDialog("Data dump in progress: ", None, 0, worst_case_scenario, self.gui)
        progress_bar.setWindowTitle("Outputting files...")
        progress_bar.setWindowModality(Qt.WindowModality.WindowModal)
        progress_bar.setValue(current_count)

        # Prealloc
        previous_pointer = 0

        # Sort our tags so they are in order of the appearance in the history
        self.tags = {k: v for k, v in sorted(self.tags.items(), key=lambda items: self.history.index(items[1].get_associated_entry_key()))}

        # Loop through our tags as they represent our output targets
        cache = dict()
        for tag in self.tags.values():
            output_target = tag.get_tag_target()

            if output_target is None or output_target == "" or output_target == "NONE":
                current_count += len(self.categories)
                progress_bar.setValue(current_count)
                continue

            try:
                worksheet = self.gsheets_connector.open(output_target)
            except ConnectionAbortedError:
                self.gsheets_connector = build_gsheets_communicator(file_path=self.gsheets_credentials_path)
                worksheet = self.gsheets_connector.open(output_target)

            # HEAD value
            target_key = tag.get_associated_entry_key()
            historical_index = self.history.index(target_key)

            # Loop through characters
            for i in range(len(self.characters)):
                character = self.characters.keys()[i]

                # Retrieve the 'Old' Sheet
                old_system_sheet = SystemSheetLayoutHandler(self.gsheets_connector, worksheet, character + " Previous View")
                old_system_sheet.clear_all()

                # Retrieve the 'Current' sheet
                system_sheet = SystemSheetLayoutHandler(self.gsheets_connector, worksheet, character + " Current View")
                system_sheet.clear_all()

                # Loop through in the correct categories order
                for category in self.characters[character]:
                    if not category.get_print_to_overview():
                        current_count += 2
                        progress_bar.setValue(current_count)
                        continue

                    # Get our previous view if applicable
                    category_name = category.get_name()
                    cache_name = character + "+" + category_name
                    if cache_name not in cache:
                        view = None
                    else:
                        view = cache[cache_name]

                    # Write our cached obj out
                    if view is not None and len(view) != 0:
                        # Write the category data (if applicable) to the system view
                        old_system_sheet.write_next([[category_name, ""]])
                        old_system_sheet.write_category_data(self, category, view)
                        # self.gsheets_connector.run_batch()

                    # Inform our UI
                    current_count += 1
                    progress_bar.setValue(current_count)

                    # Current data
                    view = self.get_category_state_for_entity_at_time(category_name, i, historical_index)

                    # This category may not exist in the past!
                    if view is not None and len(view) != 0:
                        # Write the category data (if applicable) to the system view
                        system_sheet.write_next([[category_name, ""]])
                        system_sheet.write_category_data(self, category, view)
                        # self.gsheets_connector.run_batch()

                    # Inform our UI and Update Cache
                    current_count += 1
                    progress_bar.setValue(current_count)
                    cache[cache_name] = view

            # Retrieve the history sheet
            history_sheet = HistorySheetLayoutHandler(self.gsheets_connector, worksheet, "History")
            history_sheet.clear_all()

            # Write out this tag's history in order
            history_sheet.write_historical_data(self.history, self.entries, self.categories, self.characters, previous_pointer, historical_index)
            previous_pointer = historical_index + 1
            # self.gsheets_connector.run_batch()

            current_count += 1
            progress_bar.setValue(current_count)

        # Finish up by saving - this will ensure our pointers dont get lost
        self.save()
        progress_bar.close()


if __name__ == '__main__':
    # Core
    main = LitRPGTools()

    # Trigger variable initialization
    main.start()

    # Run the console interaction
    main.run()

