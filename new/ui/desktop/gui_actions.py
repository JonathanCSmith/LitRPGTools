from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from new.data import Entry, Character, Category, Output
from new.ui.desktop.dialogs import EntryDialog, CharacterSelectorDialog, OutputSelectorDialog, CharacterDialog, CategoryDialog, OutputDialog

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


def add_or_edit_character(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', character: Character | None):
    # Build a dialog to edit the current character information
    edit_character_dialog = CharacterDialog(engine, character=character)
    edit_character_dialog.exec()

    # Validate dialog output
    if not edit_character_dialog.success:
        return

    # Check that the name is sensible
    character_name = edit_character_dialog.get_character_name()
    if not character_name[:1].isalpha():
        return

    # Add the character in our engine
    if character is None:
        character = Character(name=character_name, categories=edit_character_dialog.categories)
        engine.add_character(character)
    else:
        new_character = Character(name=character_name, categories=edit_character_dialog.categories)
        new_character.unique_id = character.unique_id
        engine.edit_character(new_character)

    # Trigger a refresh of the UI
    parent.handle_update()


def delete_character(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', character: Character):
    engine.delete_character(character)
    parent.handle_update()


def add_or_edit_category(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', category: Category | None):
    # Build a dialog to edit the current category information
    edit_category_dialog = CategoryDialog(engine, category)
    edit_category_dialog.exec()

    # Validate dialog output
    if not edit_category_dialog.success:
        return

    # Add our new category
    if category is None:
        engine.add_category(edit_category_dialog.generated_category)

    # Edit the category in our engine
    else:
        new_category = edit_category_dialog.generated_category
        new_category.unique_id = category.unique_id
        engine.edit_category(new_category, edit_category_dialog.edit_instructions)

    # Trigger a refresh of the UI
    parent.handle_update()


def delete_category(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', category: Category):
    engine.delete_category(category)
    parent.handle_update()


def set_entry_as_head(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    if entry is None:
        return

    # Set this as the current history index
    engine.set_current_history_index(entry.unique_id)
    parent.handle_update()


def add_or_edit_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry | None):
    # Different behaviour based on
    if entry is None:
        copy_entry = None
    else:
        copy_entry = Entry(entry.character_id, entry.category_id, entry.data.copy(), entry.is_disabled)

    entry_dialog = EntryDialog(engine, copy_entry, editing=True)
    entry_dialog.exec()
    if not entry_dialog.success:
        return

    # If we were a new entry, we just flat use it
    if entry is None:
        # Bail if we are still using our scaffolded entry
        if entry_dialog.entry.character_id == "MOCK" or entry_dialog.entry.category_id == "MOCK":
            return

        # Add and bail will be handled by the child == None check below
        entry = entry_dialog.entry
        engine.add_entry_at_head(entry)

    else:
        # Put the data back in the original
        entry.is_disabled = copy_entry.is_disabled
        entry.data = copy_entry.data
        entry.dynamic_data_initialisations = copy_entry.dynamic_data_initialisations
        entry.dynamic_data_operations = copy_entry.dynamic_data_operations

    # Bail if there are no children
    if entry.child_id is None:
        parent.handle_update()
        entry_index = engine.get_entry_index_in_history(entry.unique_id)
        parent.set_curently_selected(entry_index)
        return

    # Does the user want to update the children
    result = QMessageBox.question(parent, "Update children in series?", "Do you want to update this entry's children in the series?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if not result:
        parent.handle_update()
        return

    # Handle if there are children by doing a while operation on the target entry's child pointer
    target_entry = entry
    while target_entry.child_id is not None:
        target_entry = engine.get_entry_by_id(target_entry.child_id)

        # Standard editing modal dialog
        copy_entry = Entry(target_entry.character_id, target_entry.category_id, target_entry.data.copy(), target_entry.is_disabled)
        entry_dialog = EntryDialog(engine, copy_entry, editing=True)
        entry_dialog.exec()
        if not entry_dialog.success:
            continue

        # Apply the data
        target_entry.is_disabled = copy_entry.is_disabled
        target_entry.data = copy_entry.data

    # Update
    parent.handle_update()
    entry_index = engine.get_entry_index_in_history(entry.unique_id)
    parent.set_curently_selected(entry_index)


def update_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    current_entry_id = engine.get_most_recent_entry_id_in_series(entry.unique_id)

    # This situation can happen when our 'current index' is set to before the entry series has been created
    if current_entry_id is None:
        return

    # Get the 'most recent' in the series up to the current index
    current_entry = engine.get_entry_by_id(current_entry_id)
    new_entry = Entry(current_entry.character_id, current_entry.category_id, current_entry.data, current_entry.is_disabled, parent_id=current_entry.unique_id, child_id=current_entry.child_id)
    entry_dialog = EntryDialog(engine, new_entry, editing=False)
    entry_dialog.exec()
    if not entry_dialog.success:
        return

    # Apply data
    current_entry.child_id = new_entry.unique_id
    engine.add_entry_at_head(new_entry)

    # Bail if there are no children
    if new_entry.child_id is None:
        parent.handle_update()
        parent.set_curently_selected(engine.get_current_history_index())
        return

    # Does the user want to update the children
    result = QMessageBox.question(parent, "Update children in series?", "Do you want to update this entry's children in the series?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if not result:
        parent.handle_update()
        parent.set_curently_selected(engine.get_current_history_index())
        return

    # Handle if there are children by doing a while operation on the target entry's child pointer
    target_entry = new_entry
    while target_entry.child_id is not None:
        target_entry = engine.get_entry_by_id(target_entry.child_id)

        # Standard editing modal dialog
        copy_entry = Entry(target_entry.character_id, target_entry.category_id, target_entry.data.copy(), target_entry.is_disabled)
        entry_dialog = EntryDialog(engine, copy_entry, editing=True)
        entry_dialog.exec()
        if not entry_dialog.success:
            continue

        # Apply the data
        target_entry.is_disabled = copy_entry.is_disabled
        target_entry.data = copy_entry.data

    # Update
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def delete_entry_series(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    result = QMessageBox.question(parent, "Are you sure?", "Are you sure you want to delete this entry and all of the entries in the same series?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if not result:
        return

    engine.delete_entry_and_series(entry)
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def delete_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    result = QMessageBox.question(parent, "Are you sure?", "Are you sure you want to delete this entry?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if not result:
        return

    engine.delete_entry(entry)
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def duplicate_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    character_dialog = CharacterSelectorDialog(engine)
    character_dialog.exec()
    if not character_dialog.success:
        return

    # Duplicate the entry
    new_entry = Entry(character_dialog.character_id, entry.category_id, entry.data, entry.is_disabled)
    engine.add_entry_at_head(new_entry)
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def add_or_edit_output(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', original_output: Output | None):
    # If we weren't provided an output, create a dummy and have the engine 'register it' for now
    # This dummy will need to be cleaned up properly in the advent of a failure.
    if original_output is None:
        output = Output("MOCK", "MOCK", list(), list())
        engine.add_output_to_head(output)

    # Make a copy so we don't inline edit our original
    else:
        output = Output(original_output.name, original_output.gsheet_target, original_output.members, original_output.ignored)

    # Build a dialog to edit the current category information
    output_dialog = OutputDialog(engine, output)
    output_dialog.exec()

    # Validate dialog output
    if not output_dialog.success:
        return

    # Check no mock
    if output_dialog.output.name == "MOCK" or output_dialog.output.gsheet_target == "MOCK":
        return

    # Add our new category
    if original_output is None:
        engine.add_output_to_head(output_dialog.output)

    # Edit the category in our engine
    else:
        original_output.name = output_dialog.output.name
        original_output.gsheet_target = output_dialog.output.gsheet_target
        original_output.members = output_dialog.output.members
        original_output.ignored = output_dialog.output.ignored

    # Trigger a refresh of the UI
    parent.handle_update()


def delete_output(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', output: Output):
    result = QMessageBox.question(parent, "Are you sure?", "Are you sure you want to delete this output?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if not result:
        return

    engine.delete_output(output)
    parent.handle_update()
