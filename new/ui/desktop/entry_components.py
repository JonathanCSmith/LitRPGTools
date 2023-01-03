from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QPushButton, QFormLayout, QLineEdit, QPlainTextEdit, QComboBox, QMessageBox, QLabel, QCheckBox, QWidget, QVBoxLayout, QHBoxLayout

from new.data import Entry, Character, Category
from new.ui.desktop import dynamic_data_components
from new.ui.desktop.spelling_components import SpellTextEdit, SpellTextEditSingleLine

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


class EntryDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine', entry: Entry | None, editing: bool = False):
        super(EntryDialog, self).__init__()
        self.__engine = engine
        if entry is None:
            self.entry = Entry("MOCK", "MOCK", list())
            self.__new_entry = True
        else:
            self.entry = entry
            self.__new_entry = False
        self.__editing = editing
        self.success = False

        # Preallocs
        self.__character_selector = None
        self.__character_id = None
        self.__category_selector = None
        self.__category_id = None
        self.__results = list()

        # Static Buttons
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Layout
        self.__layout = QFormLayout()
        self.setLayout(self.__layout)

        # Force update
        self.__handle_update()
        self.showMaximized()

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        # Check our character
        if self.__character_id is None or self.__character_id == "" or self.__character_id == "None Selected":
            self.__handle_cancel_callback()
            return

        # Check our category
        if self.__category_id is None or self.__category_id == "" or self.__category_id == "None Selected":
            self.__handle_cancel_callback()
            return

        # Basic data
        self.entry.character_id = self.__character_id
        self.entry.category_id = self.__category_id

        # Gather our data using our callback results
        payload = list()
        for index, item in enumerate(self.__results):
            if isinstance(item, QLineEdit):
                payload.append(item.text())
            elif isinstance(item, QPlainTextEdit):
                payload.append(item.toPlainText())
        self.entry.data = payload

        # Dynamic data
        operations = dynamic_data_components.extract_dynamic_data_table_data(self.__results[-2])
        if operations is None:
            self.__handle_cancel_callback()
            return
        self.entry.dynamic_data_operations = operations

        # Final item is whether or not it was disabled
        is_disabled = self.__results[-1].isChecked()
        self.entry.is_disabled = is_disabled

        # Flags
        self.success = True
        self.close()

    def __handle_update(self):
        # Remove the rows we no longer need
        row_count = self.__layout.rowCount()
        stored_rows = list()
        for row in reversed(range(0, row_count)):
            # Do not delete our headers (for new entries only) or our buttons
            if row == row_count - 1 or (self.__new_entry and row < 2):
                stored_rows.append(self.__layout.takeRow(row))
            else:
                self.__layout.removeRow(row)

        # Depending on our state, we need to display different things
        if self.__new_entry:
            self.__handle_new_entry_update()

        else:
            self.__character_id = self.entry.character_id
            self.__category_id = self.entry.category_id

        # If we have everything we need for the form data
        if self.__character_id is not None and self.__category_id is not None:

            # Fetch data
            character = self.__engine.get_character_by_id(self.__character_id)
            category = self.__engine.get_category_by_id(self.__category_id)
            if self.__editing:
                index = self.__engine.get_entry_index_in_history(self.entry.unique_id)

            # In this case, we are making an 'update' so it gets injected at the HEAD
            else:
                index = self.__engine.get_current_history_index()

            # Add our entry to the form if possible
            self.__results = create_entry_form(self.__engine, self.__layout, character, category, self.entry, index, not self.__new_entry, False)

        # Add our buttons
        self.__layout.addRow(self.__cancel_button, self.__done_button)

    def __handle_new_entry_update(self):
        # First build
        if self.__character_selector is None:
            self.__character_selector = QComboBox()
            self.__character_selector.currentTextChanged.connect(self.__handle_update)
            self.__character_selector.blockSignals(True)
            self.__character_selector.addItem("Please Select a Character")

            # Fill in our character data
            for index, character in enumerate(self.__engine.get_characters()):
                self.__character_selector.addItem(character.name)
                self.__character_selector.setItemData(index + 1, character.unique_id, Qt.ItemDataRole.UserRole)

            self.__character_selector.blockSignals(False)

        if self.__category_selector is None:
            self.__category_selector = QComboBox()
            self.__category_selector.currentTextChanged.connect(self.__handle_update)
            self.__category_selector.blockSignals(True)
            self.__category_selector.addItem("Please Select a Character First")
            self.__category_selector.blockSignals(False)

        # The fields are always present
        self.__layout.addRow("Character:", self.__character_selector)
        self.__layout.addRow("Category:", self.__category_selector)

        # If our choice of character has changed
        current_character_id = self.__character_selector.currentData()
        if current_character_id != self.__character_id:
            self.__category_selector.blockSignals(True)
            self.__category_selector.clear()
            self.__character_id = current_character_id
            if current_character_id is None:
                self.__category_selector.addItem("Please Select a Character First")
            else:
                self.__add_categories()
            self.__category_selector.blockSignals(False)

        # Only continue if category is selected - No need to check cache here, just grab and assign no matter what
        if self.__category_selector.currentData() is not None:
            self.__category_id = self.__category_selector.currentData()
        else:
            self.__category_id = None

    def __add_categories(self):
        self.__category_selector.addItem("Please Select a Category")

        categories = self.__engine.get_categories_for_character_id(self.__character_id)
        for index, category_id in enumerate(categories):
            category = self.__engine.get_category_by_id(category_id)

            # Ignore singleton categories that already have associated data
            if category.single_entry_only:
                state = self.__engine.get_entries_for_character_and_category_at_current_history_index(self.__character_id, category_id)
                if state is not None and len(state) != 0:
                    continue

            # Add them to our drop down
            self.__category_selector.addItem(category.name)
            self.__category_selector.setItemData(index + 1, category.unique_id, Qt.ItemDataRole.UserRole)


class DoubleEntryDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine', entry: Entry, old_entry: Entry, editing: bool = False):
        super(DoubleEntryDialog, self).__init__()
        self.__engine = engine
        self.entry = entry
        self.old_entry = old_entry
        self.__editing = editing  # Used to indicate where the new entry should be injected
        self.success = False

        # Preallocs
        self.__category = None
        self.__current_data = list()
        self.__old_data = list()

        # Static Buttons
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Layout contents
        self.__old_entry_display = QWidget()
        self.__old_entry_layout = QFormLayout()
        self.__old_entry_display.setLayout(self.__old_entry_layout)
        self.__data_movement_display = QWidget()
        self.__data_movement_layout = QFormLayout()
        self.__data_movement_display.setLayout(self.__data_movement_layout)
        self.__new_entry_display = QWidget()
        self.__new_entry_layout = QFormLayout()
        self.__new_entry_display.setLayout(self.__new_entry_layout)

        # Layout
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__old_entry_display)
        self.__layout.addWidget(self.__data_movement_display)
        self.__layout.addWidget(self.__new_entry_display)
        self.setLayout(self.__layout)

        # Force update
        self.__fill_comparison_buttons()
        self.__handle_update()
        self.showMaximized()

    def __fill_comparison_buttons(self):
        self.__category = self.__engine.get_category_by_id(self.old_entry.category_id)
        empty_label = QLabel("")
        # empty_label.setStyleSheet("border: 1px solid black;")
        self.__data_movement_layout.addRow("Controls", empty_label)

        # Loop through our category contents and add our 'editing' buttons for each one.
        for index in range(len(self.__category.contents)):
            copy_previous_button = QPushButton("Copy Previous")
            copy_previous_button.clicked.connect(partial(self.__handle_copy_callback, index))
            revert_button = QPushButton("Revert to Original")
            revert_button.clicked.connect(partial(self.__handle_revert_callback, index))
            revert_button_container = QWidget()
            # revert_button_container.setStyleSheet("border: 1px solid black;")
            revert_button_layout = QVBoxLayout()
            revert_button_layout.setContentsMargins(0, 0, 0, 0)
            revert_button_layout.addWidget(revert_button)
            revert_button_layout.addStretch()
            revert_button_container.setLayout(revert_button_layout)
            self.__data_movement_layout.addRow(copy_previous_button, revert_button_container)

        # Add in a set of buttons for our dynamic data
        copy_previous_button = QPushButton("Copy Previous")
        copy_previous_button.clicked.connect(partial(self.__handle_copy_callback, -1))
        revert_button = QPushButton("Revert to Original")
        revert_button.clicked.connect(partial(self.__handle_revert_callback, -1))
        revert_button_container = QWidget()
        # revert_button_container.setStyleSheet("border: 1px solid black;")
        revert_button_layout = QVBoxLayout()
        revert_button_layout.setContentsMargins(0, 0, 0, 0)
        revert_button_layout.addWidget(revert_button)
        revert_button_layout.addStretch()
        revert_button_container.setLayout(revert_button_layout)
        self.__data_movement_layout.addRow(copy_previous_button, revert_button_container)

        # Add our 'finish' buttons
        self.__data_movement_layout.addRow(self.__cancel_button, self.__done_button)

    def __handle_copy_callback(self, index):
        if index == -1:
            dynamic_data_components.fill_dynamic_modifications_table(self.__current_data[-2], self.old_entry.dynamic_data_operations)
            return

        data_to_copy = self.old_entry.data[index]
        self.__current_data[index].setPlainText(data_to_copy)

    def __handle_revert_callback(self, index):
        if index == -1:
            dynamic_data_components.fill_dynamic_modifications_table(self.__current_data[-2], self.entry.dynamic_data_operations)
            return

        data_to_copy = self.entry.data[index]
        self.__current_data[index].setPlainText(data_to_copy)

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        # Gather our data using our callback results
        payload = list()
        for index, item in enumerate(self.__current_data):
            if isinstance(item, QLineEdit):
                payload.append(item.text())
            elif isinstance(item, QPlainTextEdit):
                payload.append(item.toPlainText())
        self.entry.data = payload

        # Dynamic data
        operations = dynamic_data_components.extract_dynamic_data_table_data(self.__current_data[-2])
        if operations is None:
            self.__handle_cancel_callback()
            return
        self.entry.dynamic_data_operations = operations

        # Final item is whether or not it was disabled
        is_disabled = self.__current_data[-1].isChecked()
        self.entry.is_disabled = is_disabled

        # Flags
        self.success = True
        self.close()

    def __handle_update(self):
        # Remove the rows we no longer need
        row_count = self.__old_entry_layout.rowCount()
        for row in range(0, row_count):
            self.__old_entry_layout.removeRow(0)
        row_count = self.__new_entry_layout.rowCount()
        for row in range(0, row_count):
            self.__new_entry_layout.removeRow(0)

        # Apply the data from the old entry
        character = self.__engine.get_character_by_id(self.old_entry.character_id)
        old_index = self.__engine.get_entry_index_in_history(self.old_entry.unique_id)
        self.__old_data = create_entry_form(self.__engine, self.__old_entry_layout, character, self.__category, self.old_entry, old_index, header=True, readonly=True, translate_with_dyanmic_data=False)
        if self.__editing:
            index = self.__engine.get_entry_index_in_history(self.entry.unique_id)
        else:
            index = self.__engine.get_current_history_index()
        self.__current_data = create_entry_form(self.__engine, self.__new_entry_layout, character, self.__category, self.entry, index, header=True, readonly=False, translate_with_dyanmic_data=False)

        # Attempt to make the rows the same height for our buttons as the data displays...
        row_count = self.__old_entry_layout.rowCount() - 1
        header_size = 14  # Magic number to account for qframelayouts additional borders
        for row in range(0, row_count):
            # label_item = self.__old_entry_layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
            layout_item = self.__old_entry_layout.itemAt(row, QFormLayout.ItemRole.FieldRole)

            if row < 3:
                if layout_item is not None:
                    header_size += layout_item.sizeHint().height()
                    #print("Header updated to: " + str(header_size) + " from field: " + label_item.widget().text() + " at loop index: " + str(row))
                continue

            elif row == 3:
                target = self.__data_movement_layout.itemAt(0, QFormLayout.ItemRole.LabelRole)
                if layout_item is not None:
                    header_size += layout_item.sizeHint().height()
                if target is not None:
                    target.widget().setFixedHeight(header_size)
                    #print("Assigning row 0 in target the height: " + str(header_size) + " at loop index: " + str(row))
            else:
                target = self.__data_movement_layout.itemAt(row - 3, QFormLayout.ItemRole.FieldRole)
                if layout_item is not None and target is not None:
                    height = layout_item.sizeHint().height()

                    # Different widgets need a little 'fudging' to get them to align correctly
                    if isinstance(layout_item.widget(), SpellTextEditSingleLine):
                        height += 0
                    elif isinstance(layout_item.widget(), SpellTextEdit):
                        height += 12

                    target.widget().setFixedHeight(height)
                    #print("Mutating target row: " + str(row - 3) + " with text to have height: " + str(height) + " from " + label_item.widget().text() + " at row index " + str(row))


def set_entry_as_head(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    if entry is None:
        return

    # Set this as the current history index
    index = engine.get_entry_index_in_history(entry.unique_id)
    engine.set_current_history_index(index)
    parent.handle_update()


def add_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI'):
    entry_dialog = EntryDialog(engine, None, editing=True)
    entry_dialog.exec()
    if not entry_dialog.success:
        return

    # Bail if we are still using our scaffolded entry
    if entry_dialog.entry.character_id == "MOCK" or entry_dialog.entry.category_id == "MOCK":
        return

    # Add and bail will be handled by the child == None check below
    entry = entry_dialog.entry
    engine.add_entry_at_head(entry)

    # Deal GUI update
    parent.handle_update()
    entry_index = engine.get_entry_index_in_history(entry.unique_id)
    parent.set_curently_selected(entry_index)


def edit_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    copy_entry = Entry(entry.character_id, entry.category_id, entry.data.copy(), entry.is_disabled, dynamic_data_operations=entry.dynamic_data_operations)
    copy_entry.unique_id = entry.unique_id  # TODO: Would it be simpler to just reuse the existing
    if entry.parent_id is not None:
        old_entry = engine.get_entry_by_id(entry.parent_id)
        entry_dialog = DoubleEntryDialog(engine, copy_entry, old_entry, editing=True)
    else:
        entry_dialog = EntryDialog(engine, copy_entry, editing=True)

    entry_dialog.exec()
    if not entry_dialog.success:
        return

    # Put the data back in the original
    entry.is_disabled = copy_entry.is_disabled
    entry.data = copy_entry.data
    entry.dynamic_data_operations = copy_entry.dynamic_data_operations
    engine.edit_entry(entry)

    # Bail if there are no children
    if entry.child_id is None:
        parent.handle_update()
        entry_index = engine.get_entry_index_in_history(entry.unique_id)
        parent.set_curently_selected(entry_index)
        return

    # Does the user want to update the children
    result = QMessageBox.question(parent, "Update children in series?", "Do you want to update this entry's children in the series?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if result != QMessageBox.StandardButton.Yes:
        parent.handle_update()
        return

    # Handle if there are children by doing a while operation on the target entry's child pointer
    old_entry = entry
    target_entry = entry
    while target_entry.child_id is not None:
        target_entry = engine.get_entry_by_id(target_entry.child_id)

        # Standard editing modal dialog
        copy_entry = Entry(target_entry.character_id, target_entry.category_id, target_entry.data.copy(), target_entry.is_disabled, dynamic_data_operations=target_entry.dynamic_data_operations)
        copy_entry.unique_id = target_entry.unique_id  # TODO: Would it be simpler to just reuse the existing
        entry_dialog = DoubleEntryDialog(engine, copy_entry, old_entry, editing=True)
        entry_dialog.exec()
        if not entry_dialog.success:
            continue

        # Apply the data
        target_entry.is_disabled = copy_entry.is_disabled
        target_entry.data = copy_entry.data
        target_entry.dynamic_data_operations = copy_entry.dynamic_data_operations
        engine.edit_entry(target_entry)

        # Loop continuation
        old_entry = target_entry

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
    new_entry = Entry(current_entry.character_id, current_entry.category_id, current_entry.data, current_entry.is_disabled, dynamic_data_operations=entry.dynamic_data_operations, parent_id=current_entry.unique_id, child_id=current_entry.child_id)
    new_entry.unique_id = current_entry.unique_id  # TODO: Would it be simpler to just reuse the existing
    entry_dialog = DoubleEntryDialog(engine, new_entry, current_entry, editing=False)
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
    if result != QMessageBox.StandardButton.Yes:
        parent.handle_update()
        parent.set_curently_selected(engine.get_current_history_index())
        return

    # Handle if there are children by doing a while operation on the target entry's child pointer
    old_entry = current_entry
    target_entry = current_entry
    while target_entry.child_id is not None:
        target_entry = engine.get_entry_by_id(target_entry.child_id)

        # Standard editing modal dialog
        copy_entry = Entry(target_entry.character_id, target_entry.category_id, target_entry.data.copy(), target_entry.is_disabled, dynamic_data_operations=target_entry.dynamic_data_operations)
        copy_entry.unique_id = target_entry.unique_id  # TODO: Would it be simpler to just reuse the existing
        entry_dialog = DoubleEntryDialog(engine, copy_entry, old_entry, editing=True)
        entry_dialog.exec()
        if not entry_dialog.success:
            continue

        # Apply the data
        target_entry.is_disabled = copy_entry.is_disabled
        target_entry.data = copy_entry.data
        target_entry.dynamic_data_operations = copy_entry.dynamic_data_operations
        engine.edit_entry(target_entry)

        # Loop continuation
        old_entry = target_entry

    # Update
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def delete_entry_series(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    result = QMessageBox.question(parent, "Are you sure?", "Are you sure you want to delete this entry and all of the entries in the same series?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if result != QMessageBox.StandardButton.Yes:
        return

    engine.delete_entry_and_series(entry)
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def delete_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    result = QMessageBox.question(parent, "Are you sure?", "Are you sure you want to delete this entry?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if result != QMessageBox.StandardButton.Yes:
        return

    engine.delete_entry(entry)
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def duplicate_entry(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    from new.ui.desktop.character_components import CharacterSelectorDialog
    character_dialog = CharacterSelectorDialog(engine)
    character_dialog.exec()
    if not character_dialog.success:
        return

    # Duplicate the entry
    new_entry = Entry(character_dialog.character_id, entry.category_id, entry.data, entry.is_disabled, dynamic_data_operations=entry.dynamic_data_operations)
    engine.add_entry_at_head(new_entry)
    parent.handle_update()
    parent.set_curently_selected(engine.get_current_history_index())


def create_entry_form(engine: 'LitRPGToolsEngine', target_layout: QFormLayout, character: Character | None, category: Category, entry: Entry | None, history_index: int, header=True, readonly=False, translate_with_dyanmic_data=False) -> list:
    # Add our header info
    if header:
        target_layout.addRow("Character:", QLabel(character.name))
        target_layout.addRow("Category:", QLabel(category.name))
        target_layout.addRow("History Index:", QLabel(str(history_index)))
        target_layout.addRow("", QLabel())

    # Add our contents
    callback_for_editables = []
    for index, (key, large_input) in enumerate(category.contents.items()):

        # This try/except allows us to handle entries that haven't been fully initialised yet.
        try:
            data = entry.data[index]
        except IndexError as e:
            data = ""

        if translate_with_dyanmic_data:
            data = engine.translate_using_dynamic_data_at_index_for_character(character.unique_id, data, history_index)

        # Kind of field
        if large_input:
            input_field = SpellTextEdit(data)
        else:
            input_field = SpellTextEditSingleLine(data)

        # Ensure the field is not editable
        if readonly:
            input_field.setReadOnly(True)

        target_layout.addRow(key, input_field)
        callback_for_editables.append(input_field)

    # Dynamic data modifications
    modifications_table = dynamic_data_components.create_dynamic_data_table(readonly=readonly)
    if entry is not None and entry.dynamic_data_operations:
        dynamic_data_components.fill_dynamic_modifications_table(modifications_table, entry.dynamic_data_operations, readonly=readonly)
    target_layout.addRow("Dynamic Data:", modifications_table)
    callback_for_editables.append(modifications_table)

    # Add display for 'disabled'
    check_box = QCheckBox()
    if entry is not None:
        check_box.setChecked(entry.is_disabled)
    if readonly:
        check_box.setEnabled(False)
    target_layout.addRow("Is Disabled?", check_box)
    callback_for_editables.append(check_box)
    return callback_for_editables


def create_entry_form_with_controls(target_layout, engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    character = engine.get_character_by_id(entry.character_id)
    category = engine.get_category_by_id(entry.category_id)
    entry_index = engine.get_entry_index_in_history(entry.unique_id)

    # Form
    entry_form = QWidget()
    entry_form_layout = QFormLayout()
    create_entry_form(engine, entry_form_layout, character, category, entry, entry_index, translate_with_dyanmic_data=parent.get_should_display_dynamic())
    entry_form.setLayout(entry_form_layout)

    # Controls
    entry_controls = QWidget()
    entry_controls_layout = QVBoxLayout()
    set_as_head_button = QPushButton("Set as Current Entry in History")
    set_as_head_button.clicked.connect(partial(set_entry_as_head, engine, parent, entry))
    entry_controls_layout.addWidget(set_as_head_button)
    # set_as_selected_button = QPushButton("Highlight all entries in series.")
    # set_as_selected_button.clicked.connect(partial(parent.set_curently_selected, entry_index))
    # entry_controls_layout.addWidget(set_as_selected_button)
    entry_edit_button = QPushButton("Edit")
    entry_edit_button.clicked.connect(partial(edit_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_edit_button)
    entry_update_button = QPushButton("Update")
    entry_update_button.clicked.connect(partial(update_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_update_button)
    entry_series_delete_button = QPushButton("Delete Series")
    entry_series_delete_button.clicked.connect(partial(delete_entry_series, engine, parent, entry))
    entry_controls_layout.addWidget(entry_series_delete_button)
    entry_delete_button = QPushButton("Delete")
    entry_delete_button.clicked.connect(partial(delete_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_delete_button)
    entry_duplicate_button = QPushButton("Duplicate")
    entry_duplicate_button.clicked.connect(partial(duplicate_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_duplicate_button)
    entry_controls_layout.addStretch()
    # spacer = QWidget()
    # entry_controls_layout.addWidget(spacer)
    # entry_controls_layout.setStretchFactor(spacer, 100)
    # entry_controls_layout.setContentsMargins(0, 0, 0, 0)
    entry_controls.setLayout(entry_controls_layout)

    # Main container
    entry_widget = QWidget()
    entry_widget_layout = QHBoxLayout()
    entry_widget_layout.addWidget(entry_form)
    entry_widget_layout.setStretchFactor(entry_form, 90)
    entry_widget_layout.addWidget(entry_controls)
    entry_widget_layout.setStretchFactor(entry_controls, 10)
    entry_widget_layout.setContentsMargins(0, 0, 0, 0)
    entry_widget.setObjectName("bordered")
    entry_widget.setLayout(entry_widget_layout)
    target_layout.addWidget(entry_widget)
