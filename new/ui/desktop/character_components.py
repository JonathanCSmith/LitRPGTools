from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QLineEdit, QTableWidget, QPushButton, QFormLayout, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox

from new.data import Character
from new.ui.desktop.custom_generic_components import add_checkbox_in_table_at

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


class CharacterDialog(QDialog):
    def __init__(self, engine, character=None):
        super(CharacterDialog, self).__init__()
        self.__engine = engine
        self.success = False
        self.categories = list()

        # General
        if character is None:
            self.setWindowTitle("New Character")
        else:
            self.setWindowTitle("Edit Character")

        # Form content
        self.__character_name_field = QLineEdit()
        self.__character_categories_table = QTableWidget()
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Layout
        self.layout = QFormLayout()
        self.layout.addRow("Character Name: ", self.__character_name_field)
        self.layout.addRow("Character categories: ", self.__character_categories_table)
        self.layout.addRow(self.__cancel_button, self.__done_button)
        self.setLayout(self.layout)

        # Fill in our character name if required
        self.__character = character
        if character is not None:
            self.__character_name_field.setText(character.name)

        # Fill our character categories table
        self.__character_categories_table.setColumnCount(2)
        self.__character_categories_table.setHorizontalHeaderItem(0, QTableWidgetItem("Category"))
        self.__character_categories_table.setHorizontalHeaderItem(1, QTableWidgetItem("Enabled?"))
        self.__character_categories_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.__character_categories_table.blockSignals(True)
        categories = self.__engine.get_categories()
        self.__character_categories_table.setRowCount(len(categories))
        for i, category in enumerate(categories):
            self.__character_categories_table.setItem(i, 0, QTableWidgetItem(category.name))

            # Check whether or not this character cares about this state at all
            if self.__character is None:
                state = False
            else:
                state = category.unique_id in self.__character.categories

            # Add a checkbox to allow the user to register the interest of this character in
            add_checkbox_in_table_at(self.__character_categories_table, 0, state=state, callback=partial(self.__handle_toggle_category_callback, category.unique_id))

            # Add +ves to our cache for output
            if state:
                self.categories.append(category.unique_id)
        self.__character_categories_table.blockSignals(False)

    def __handle_toggle_category_callback(self, category_id):
        if category_id in self.categories:
            self.categories.remove(category_id)
        else:
            self.categories.append(category_id)

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        # Check if an item has been removed from our original input list
        if self.__character is not None and not set(self.__character.categories).issubset(self.categories):
            result = QMessageBox.question(self, "Are you sure?", "You have removed a category from a character. This will result in all associated entries from that character+category combination from being deleted. Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            self.success = result == QMessageBox.StandardButton.Yes
        else:
            self.success = True
        self.close()

    def get_character_name(self):
        return self.__character_name_field.text()


class CharacterSelectorDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self.__engine = engine
        self.success = False
        self.character_id = None

        # Character selector
        self.__character_selector = QComboBox()
        self.__character_selector.addItem("Please Select A Character")

        # Fill in our character data
        for index, character in enumerate(self.__engine.get_characters()):
            self.__character_selector.addItem(character.name)
            self.__character_selector.setItemData(index + 1, character.unique_id, Qt.ItemDataRole.UserRole)

        # Buttons
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Layout
        self.__layout = QFormLayout()
        self.__layout.addRow("Character:", self.__character_selector)
        self.__layout.addRow(self.__cancel_button, self.__done_button)
        self.setLayout(self.__layout)

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        self.character_id = self.__character_selector.currentData()
        self.success = True if self.character_id is not None else False
        self.close()


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
