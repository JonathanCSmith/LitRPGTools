from PyQt6.QtWidgets import QMessageBox

from data.entries import Entry
from gui.entry_dialogs import EditEntryDialog


def handle_update_later_entries(engine, just_added_key):
    # Get the child for this key
    child_key = engine.get_child_key_from_parent_key(just_added_key)
    if child_key is None:
        return

    # Ask if we want to child entries
    reply = QMessageBox()
    reply.setText("Do you wish to edit all entries following this one?")
    reply.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    reply = reply.exec()
    if reply != QMessageBox.StandardButton.Yes:
        return

    # While loop childwards
    while child_key is not None:
        # Display an update dialog for this entry
        create_edit_dialog(engine, child_key)
        child_key = engine.get_child_key_from_parent_key(child_key)


def create_edit_dialog(main, entry_key_to_update):
    entry = main.get_entry(entry_key_to_update)
    category = main.get_category(entry.get_category())

    # Create an edit entry dialog
    entry_dialog = EditEntryDialog(category, entry.get_values(), entry.get_print_to_overview(), entry.print_to_history)
    entry_dialog.exec()
    if entry_dialog.viable:
        main.update_existing_entry_values(entry_key_to_update, entry_dialog.get_data(), should_print_to_overview=entry_dialog.print_to_overview.isChecked(), should_print_to_history=entry_dialog.print_to_history.isChecked())
    return entry_dialog.viable


def create_update_dialog(engine, entry_key_to_update):
    # Get the 'latest' entry in the series up to our current 'head'.
    absolute_root_key = engine.get_absolute_parent(entry_key_to_update)
    if absolute_root_key is not None:
        target_key = engine.get_most_recent_revision_for_root_entry_key(absolute_root_key)
    else:
        target_key = entry_key_to_update

    # Get the real data
    target_entry = engine.get_entry(entry_key_to_update)
    category = engine.get_category(target_entry.get_category())

    # Create an update entry dialog
    entry_dialog = EditEntryDialog(category, target_entry.get_values(), target_entry.get_print_to_overview(), target_entry.print_to_history)
    entry_dialog.exec()
    if entry_dialog.viable:
        entry = Entry(
            target_entry.get_category(),
            entry_dialog.get_data(),
            parent_key=target_key,
            print_to_overview=entry_dialog.print_to_overview.isChecked(),
            character=target_entry.character,
            print_to_history=entry_dialog.print_to_history.isChecked())

        engine.add_entry(entry)
    return entry_dialog.viable