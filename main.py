import json
import os.path
import sys
from collections import OrderedDict
from typing import Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QProgressDialog
from indexed import IndexedOrderedDict

import utils
import search_helper
from data import Character, Entry, Category, Output, DataFile
from dynamic import DynamicDataStore
from gsheets import GSheetsHandler
from ui.desktop.gui import LitRPGToolsDesktopGUI
from utils import handle_old_save_file_loader

"""
High Priority:
TODO: Filters on the history view.
TODO: Changes on character name didn't propagate (but were in save file) - update issue?
TODO: Enter = run search
TODO: Autosave to remember default save path?
TODO: If an entry is not updatable then dont display the update buttons (note, force update should still be allowed!)

Low Priority:
TODO: Search shouldn't be tokenised??? 
TODO: Catch likely candidates (e.g. '[string]') and assume we intended it a string literal?
TODO: Create entry everywhere with context applied?
TODO: Fill in options (i.e. for create entry) when there is only one choice
TODO: OS X saving seems to put it in the wrong directory (uses relative to cwd?)
TODO: Expression creator!
TODO: Update function logic check + streamline?
TODO: Better notifications when things go wrong
TODO: History log text inject category info etc etc
TODO: Replace in search?
TODO: Mobile?
TODO: Web
TODO: Bullet Points and Bold?
TODO: Switch to Deltas?
TODO: Versionable Categories?
TODO: NamedRanges ordering
"""


class LitRPGToolsEngine:
    def __init__(self):
        self.runtime = QApplication(sys.argv)
        self.gui = None

        # Runtime flags
        self.started = False

        # Permanent Data
        self.__history = list()
        self.__outputs: OrderedDict[str, Output] = OrderedDict()
        self.__characters = IndexedOrderedDict()
        self.__categories = IndexedOrderedDict()
        self.__entries: Dict[str, Entry] = dict()

        # Ephemeral Cache Data (Volatile)
        self.__character_category_root_entry_cache = dict()  # Character id index -> Category id index -> list of entries (only roots!)
        self.__revision_indices = dict()  # All entries -> revision key (which is actually revision root id but hey-ho)
        self.__revisions = dict()  # revision key (which is actually revision root id) -> ordered list of revisions
        self.__entry_id_to_output_cache = dict()  # Map entry to outputs where said entry is the target

        # Runtime data
        self.file_save_path = None
        self.__history_index = -1
        self.__value_store = dict()
        self.__gsheets_credentials_path = None
        self.__gsheets_handler: GSheetsHandler = None

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
        # We assume this is already set somewhere as our engine doesn't know about guis (NOTE, doesn't have to be this way. GUIs could implement an interface/mixin)
        if self.file_save_path is None:
            return
        self.__save(self.file_save_path)

    def load(self):
        # We assume this is already set somewhere as our engine doesn't know about guis (NOTE, doesn't have to be this way. GUIs could implement an interface/mixin)
        if self.file_save_path is None:
            return
        self.__load(self.file_save_path)

    def save_autosave(self):
        self.__save("autosave.litrpg")

    def has_autosave(self):
        return os.path.isfile("autosave.litrpg")

    def load_autosave(self):
        self.__load("autosave.litrpg")

    def delete_autosave(self):
        if os.path.isfile("autosave.litrpg"):
            os.remove("autosave.litrpg")

    def __save(self, path: str):
        data_holder = DataFile(self.__characters, self.__categories, self.__history, self.__entries, self.__outputs, self.__gsheets_credentials_path, self.__history_index)
        jsons = json.dumps(data_holder, default=lambda o: o.__dict__, indent=4)
        with open(path, "w") as output_file:
            output_file.write(jsons)

    def __load(self, path: str):
        with open(path, "r") as source_file:
            json_data = json.load(source_file)
            if "file_version" not in json_data:
                data_handler = handle_old_save_file_loader(json_data)
                if data_handler is None:
                    return

            else:
                data_handler = DataFile.from_json(json_data)

        # Unpack the data
        self.__characters = data_handler.characters
        self.__categories = data_handler.categories
        self.__entries = data_handler.entries
        self.__outputs = data_handler.outputs
        self.__history = data_handler.history
        self.__history_index = data_handler.history_index

        # Rebuild our caches
        self.__rebuild_caches()
        if self.gui is not None:
            self.gui.draw()

        # Setup gsheets - bail if it's not a valid path
        # TODO: This may be confusing as the user may expect their path to work and it won't (changed locations, shared save etc)
        gsheets_credentials = data_handler.gsheets_credentials_path
        if gsheets_credentials is not None and gsheets_credentials != "" and os.path.isfile(gsheets_credentials):
            self.load_gsheets_credentials(gsheets_credentials)

    def load_gsheets_credentials(self, file: str):
        self.__gsheets_handler = GSheetsHandler(self, self.gui, file)
        self.__gsheets_credentials_path = file

    def get_unassigned_gsheets(self):
        if self.__gsheets_handler is None:
            return None

        sheets = self.__gsheets_handler.get_sheets()
        for output in self.__outputs.values():
            if output.gsheet_target in sheets:
                sheets.remove(output.gsheet_target)
        return sheets

    def output_to_gsheets(self):
        self.save()

        # Progress metrics
        current_work_done = 0
        worst_case_max_work = len(self.__outputs) * len(self.__entries) * len(self.__characters) * 2 * 2  # 2 is from history AND overview. 2 is from us outputting old version too

        # TODO: This is not implementation independent, if we ever change front ends this will need to be abstracted
        progress_bar = QProgressDialog("Data output in progress: ", None, 0, worst_case_max_work, self.gui)
        progress_bar.setWindowTitle("Outputting data.")
        progress_bar.setWindowModality(Qt.WindowModality.WindowModal)
        progress_bar.setValue(current_work_done)

        # Loop through outputs
        last_seen = -1
        view_cache = dict()  # Because we are printing a rolling window of 2 outputs per output, we may as well cache
        for output in self.__outputs.values():
            estimate_work_done = current_work_done

            # Skip bad outputs
            if output.gsheet_target is None or output.gsheet_target == "" or output.gsheet_target == "NONE":
                current_work_done += len(self.__entries) * len(self.__characters) * 2 * 2
                progress_bar.setValue(current_work_done)
                continue

            # Open up our target
            try:
                self.__gsheets_handler.open(output.gsheet_target)
            except ConnectionAbortedError:
                self.__gsheets_handler.connect()
                self.__gsheets_handler.open(output.gsheet_target)

            # Determine our 'output' last entry props
            target_index = self.get_entry_index_in_history(output.target_entry_id)

            # Operate on a per character basis
            for character in self.__characters.values():

                # Create a 'view' for our previous output - so that it can easily be referenced from one document
                if last_seen != -1:

                    # Clear out our old sheets
                    old_system_sheet = self.__gsheets_handler.create_overview_sheet(character + " Previous View")
                    old_system_sheet.clear_all()

                    # Loop through on a per category basis
                    for category_id in self.__characters[character.unique_id].categories:
                        category = self.__categories[category_id]

                        # Skip those who don't need outputting
                        if not category.print_to_character_overview:
                            estimate_work_done += 2
                            progress_bar.setValue(estimate_work_done)
                            continue

                        # Get a 'view' of the current state of a category for a character
                        # It's also guaranteed not to be empty as we skip the first
                        output_instance_view = view_cache[category_id + "_" + category.unique_id + "_" + str(target_index)]

                        # Write out our data
                        old_system_sheet.write(self, category, output_instance_view, target_index)

                        # Progress bar update
                        estimate_work_done += 2
                        progress_bar.setValue(estimate_work_done)

                # Clear out our current sheet
                system_sheet = self.__gsheets_handler.create_overview_sheet(character.name + " Current View")
                system_sheet.clear_all()

                # Loop through on a per category basis
                for category_id in self.__characters[character.unique_id].categories:
                    category = self.__categories[category_id]

                    # Skip those who don't need outputting
                    if not category.print_to_character_overview:
                        estimate_work_done += 2
                        progress_bar.setValue(estimate_work_done)
                        continue

                    # Get a 'view' of the current state of a category for a character
                    # It's also guaranteed not to be empty as we skip the first
                    output_instance_view = self.get_entries_for_character_and_category_at_history_index(character.unique_id, category_id, target_index)
                    view_cache[category_id + "_" + category.unique_id + "_" + str(target_index)] = output_instance_view

                    # Write out our data
                    system_sheet.write(self, category, output_instance_view, target_index)

                    # Progress bar update
                    estimate_work_done += 2
                    progress_bar.setValue(estimate_work_done)

                # Correct our progressbar estimate
                current_work_done += len(self.__entries) * 2
                progress_bar.setValue(current_work_done)

            # Output our history sheet
            history_sheet = self.__gsheets_handler.create_history_sheet()
            history_sheet.clear_all()
            history_sheet.write(self, output)

            # Further correct our progress bar - now you can see how bad the estimate was!
            current_work_done += len(self.__entries) * len(self.__characters) * 2
            progress_bar.setValue(current_work_done)

        # If we were successful save and finish!
        progress_bar.close()
        self.save()

    def get_character_ids(self):
        return self.__characters.keys()

    def get_characters(self) -> List[Character]:
        return self.__characters.values()

    def get_character_by_id(self, character_id: str) -> Character | None:
        if character_id in self.__characters:
            return self.__characters[character_id]
        return None

    def move_character_id_by_index_to_index(self, from_index, to_index):
        self.__characters = utils.move_item_in_iod_by_index_to_position(self.__characters, from_index, to_index)

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

    def get_category_by_id(self, category_id: str) -> Category | None:
        if category_id in self.__categories:
            return self.__categories[category_id]
        return None

    def move_category_id_by_index_to_index(self, character_id: str, from_index, to_index):
        if character_id not in self.__characters:
            return

        character = self.get_character_by_id(character_id)
        character.categories = utils.move_item_in_list_by_index_to_position(character.categories, from_index, to_index)

    def add_category(self, category: Category, rebuild_caches=True):
        if category not in self.__categories:
            self.__categories[category.unique_id] = category

            # This is excessive here - we can shortcut if its performance heavy
            if rebuild_caches:
                self.__rebuild_caches()

    def edit_category(self, category: Category, edit_instructions: list):
        self.__categories[category.unique_id] = category

        # Loop through all the entries associated with a category and update according to the edit instructions
        for character_id in self.__character_category_root_entry_cache:
            if category.unique_id not in self.__characters[character_id].categories:
                continue

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
        self.save_autosave()

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

    def get_outputs(self) -> List[Output]:
        return self.__outputs.values()

    def get_output_by_id(self, output_id: str) -> Output | None:
        if output_id in self.__outputs:
            return self.__outputs[output_id]
        return None

    def move_output_target_up_by_id(self, output_id: str, rebuild_caches=True):
        if output_id not in self.__outputs:
            return

        # Bail if its a bad move
        output = self.__outputs[output_id]
        target_entry_id = output.target_entry_id
        target_index = self.get_entry_index_in_history(target_entry_id)
        if target_index == 0:
            return

        # Check if the new entry has an output
        new_target_entry_id = self.get_entry_id_by_history_index(target_index - 1)
        if new_target_entry_id in self.__entry_id_to_output_cache:
            return

        # Assign
        output.target_entry_id = new_target_entry_id

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def move_output_target_down_by_id(self, output_id: str, rebuild_caches=True):
        if output_id not in self.__outputs:
            return

        # Bail if its a bad move
        output = self.__outputs[output_id]
        target_entry_id = output.target_entry_id
        target_index = self.get_entry_index_in_history(target_entry_id)
        if target_index == len(self.__history) - 1:
            return

        # Check if the new entry has an output
        new_target_entry_id = self.get_entry_id_by_history_index(target_index + 1)
        if new_target_entry_id in self.__entry_id_to_output_cache:
            return

        # Assign
        output.target_entry_id = new_target_entry_id

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def add_output_to_head(self, output: Output, rebuild_caches=True):
        if output.unique_id in self.__outputs:
            return

        # Check if we already have an output targeting this entry
        target_entry_id = self.get_most_recent_entry_id()
        if target_entry_id in self.__entry_id_to_output_cache:
            return

        # Assign the data
        output.target_entry_id = target_entry_id
        self.__outputs[output.unique_id] = output

        # Rebuild caches
        if rebuild_caches:
            self.__rebuild_caches()

    def edit_output(self, output: Output):
        if output.unique_id not in self.__outputs:
            return

        self.__outputs[output.unique_id] = output

        # Update our dynamic data store
        self.__dynamic_data_store.update()
        self.save_autosave()

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

    def get_root_entry_id_in_series(self, entry_id: str):
        if entry_id not in self.__entries:
            return None

        revisions = self.get_entry_revisions_for_id(entry_id)
        if revisions is None:
            print("Badly formed revisions? Need to rebuild caches somewhere?")
            return None

        return revisions[0]

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
        return self.get_entries_for_character_and_category_at_history_index(character_id, category_id, self.get_current_history_index())

    def get_entries_for_character_and_category_at_history_index(self, character_id: str, category_id: str, target_index: int) -> list[str] | None:
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
                if index <= target_index:
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
        target_index = self.get_current_history_index() + 1
        self.__add_entry_at(entry, target_index, rebuild_caches=False)
        self.set_current_history_index(target_index)

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
        self.save_autosave()

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
            parent_entry.child_id = None
        elif child_entry is not None:  # Have only a child
            child_entry.parent_id = None

        # Handle if we have an output tagged to this entry
        if entry.unique_id in self.__entry_id_to_output_cache:
            output = self.get_output_by_id(self.__entry_id_to_output_cache[entry.unique_id])
            current_index = self.__history.index(entry.unique_id)

            # Handle which entry we are attempting to target based on our current position
            if current_index == 0 or self.__history[current_index - 1] in self.__entry_id_to_output_cache:
                self.delete_output(output, rebuild_caches=False)
            else:
                # Get our target information
                target_entry_id = self.__history[current_index - 1]
                output.target_entry_id = target_entry_id

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
        elif index > len(self.__entries) - 1:
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
        if index <= self.__history_index:
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
        elif rebuild_caches:
            self.__rebuild_caches()

    def __rebuild_caches(self):
        self.__revision_indices.clear()
        self.__revisions.clear()
        self.__character_category_root_entry_cache.clear()
        self.__entry_id_to_output_cache.clear()

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
                    if entry is None:
                        print("WTF")

                # Store revisions
                self.__revisions[unique_key] = revisions_list

                # Cache our knowledge regarding an entry's character and category so we don't have to look for them
                self.__character_category_root_entry_cache[entry.character_id][entry.category_id].append(unique_key)

        # Sort outputs based on their target index
        for value in sorted(self.__outputs.values(), key=lambda item: self.get_entry_index_in_history(item.target_entry_id)):
            self.__outputs.move_to_end(value.unique_id)

        # Rebuild output contents in case they changed
        last_seen = -1
        for output_id, output in self.__outputs.items():
            target_id = output.target_entry_id
            target_index = self.get_entry_index_in_history(target_id)

            # Rebuild our output contents
            valid_entries = list()
            for output_entry_index in range(last_seen + 1, target_index + 1):
                output_member_id = self.get_entry_id_by_history_index(output_entry_index)
                valid_entries.append(output_member_id)

                # Determine if the entry is new to us and if so add it to 'ignored'
                if output_member_id not in output.members and output_member_id not in output.ignored:
                    output.ignored.append(output_member_id)

            # Check for entries remembered by the output and remove any that dont exist
            to_remove = list()
            for output_member_id in output.members:
                if output_member_id not in valid_entries:
                    to_remove.append(output_member_id)
            for output_member_id in to_remove:
                output.members.remove(output_member_id)
            to_remove = list()
            for output_member_id in output.ignored:
                if output_member_id not in valid_entries:
                    to_remove.append(output_member_id)
            for output_member_id in to_remove:
                output.ignored.remove(output_member_id)

            # Update our 'last seen' lower bound capture
            last_seen = target_index

        # Dynamic data store
        self.__dynamic_data_store.update()

        # Autosave
        self.save_autosave()

    def get_dynamic_data_for_current_index_and_character_id(self, character_id: str, private: bool):
        return self.__dynamic_data_store.get_dynamic_data_for_character_id_at_index(self.__history_index, character_id, private)

    def translate_using_dynamic_data_at_index_for_character(self, character_id: str, input_string: str, entry_id, index: int = -1):
        if index is None or index == -1:
            index = self.__history_index
        return self.__dynamic_data_store.translate(index, character_id, entry_id, input_string)

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
