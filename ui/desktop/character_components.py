from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import QDialog, QLineEdit, QTableWidget, QPushButton, QFormLayout, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QTabWidget, QVBoxLayout, QWidget, QCheckBox

from data import Character
from ui.desktop.category_components import CategoryTab
from ui.desktop.custom_generic_components import add_checkbox_in_table_at
from ui.desktop.dynamic_data_components import DynamicDataTab

if TYPE_CHECKING:
    from main import LitRPGToolsEngine
    from ui.desktop.gui import LitRPGToolsDesktopGUI


class CharacterTab(QWidget):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine', character_id: str):
        super().__init__()
        self._parent = parent
        self._engine = engine
        self.character_id = character_id

        # Content
        self.__tabbed_view = QTabWidget()
        self.__tabbed_view.currentChanged.connect(self.__handle_tab_changed_callback)

        # Additional tabs
        self.__character_configuration_tab = CharacterConfigurationTab(self, self._engine)
        self.__dynamic_data_tab = DynamicDataTab(self._engine, self.character_id)
        self.__tabs_cache = OrderedDict()

        # Tab bar props
        self.__tabbed_view.tabBar().tabBarClicked.connect(self.__handle_tab_clicked_callback)
        self.__tabbed_view.tabBar().tabMoved.connect(self.__handle_tab_moved_callback)

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__tabbed_view)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setStretch(0, 100000)
        self.setLayout(self.__layout)

    def __handle_tab_changed_callback(self):
        tabbed_widget = self.__tabbed_view.currentWidget()
        if tabbed_widget is None:
            return
        tabbed_widget.draw()

    def __handle_tab_clicked_callback(self, index):
        if index > 1:
            self.__tabbed_view.tabBar().setMovable(True)
        else:
            self.__tabbed_view.tabBar().setMovable(False)

    def __handle_tab_moved_callback(self, target_index, source_index):
        if target_index < 2:
            with QSignalBlocker(self.__tabbed_view.tabBar()) as blocker:
                self.__tabbed_view.tabBar().moveTab(source_index, target_index)

        elif source_index > 1 and target_index > 1:
            self._engine.move_category_id_by_index_to_index(self.character_id, source_index - 2, target_index - 2)

    def draw(self):
        current_tab_index = self.__tabbed_view.currentIndex()
        current_tab_text = self.__tabbed_view.tabText(current_tab_index)

        # Block notifications
        self.__tabbed_view.blockSignals(True)

        # Refresh our tabs and store them in a list for comparison
        self.__tabbed_view.clear()

        # Fixed tabs
        self.__tabbed_view.addTab(self.__character_configuration_tab, "Character Categories")
        self.__tabbed_view.addTab(self.__dynamic_data_tab, "Dynamic Data Store")

        # Conditional addition of categories
        character = self._engine.get_character_by_id(self.character_id)
        category_ids = character.categories
        if category_ids is None:
            return

        # Work through our available categories and add
        for category_id in category_ids:
            category = self._engine.get_category_by_id(category_id)

            # Retrieve cached tab and add to tabs
            if category_id in self.__tabs_cache:
                tab = self.__tabs_cache[category_id]
            else:
                tab = CategoryTab(self, self._engine, category_id)
                self.__tabs_cache[category_id] = tab
            self.__tabbed_view.addTab(tab, category.name)

        # Remove redundant cached items
        items_to_delete = []
        for category_id in self.__tabs_cache.keys():
            if category_id not in category_ids:
                items_to_delete.append(category_id)
        for item in items_to_delete:
            self.__tabs_cache[item].deleteLater()
            del self.__tabs_cache[item]

        # Return to selected if possible
        keys = ["Character Categories", "Dynamic Data Store", self.__tabs_cache.keys()]
        if current_tab_text in keys:
            index = keys.index(current_tab_text)
            self.__tabbed_view.setCurrentIndex(index)

        # Return signals
        self.__tabbed_view.blockSignals(False)

        # defer update to tab
        w = self.__tabbed_view.currentWidget()
        if w is not None:
            w.draw()


class CharacterConfigurationTab(QWidget):
    def __init__(self, parent: CharacterTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Form layout
        self.__layout = QFormLayout()
        self.setLayout(self.__layout)

    def draw(self):
        character = self._engine.get_character_by_id(self._parent.character_id)
        if character is None:
            return

        # Remove any existing
        for index in range(self.__layout.rowCount()):
            self.__layout.removeRow(0)

        # Add in fresh
        categories = self._engine.get_categories()
        for category in categories:
            check_box = QCheckBox()
            state = category.unique_id in character.categories
            check_box.setChecked(state)
            check_box.clicked.connect(partial(self.__handle_category_box_callback, category.unique_id, state))
            self.__layout.addRow(category.name, check_box)

    def __handle_category_box_callback(self, category_id: str, current_state: bool):
        character = self._engine.get_character_by_id(self._parent.character_id)
        if current_state:
            character.categories.remove(category_id)
        else:
            character.categories.append(category_id)
        self._engine.edit_character(character)

        # Call parent so that the tabs can be updated
        self._parent.draw()


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
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

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


def add_or_edit_character(engine: 'LitRPGToolsEngine', character: Character | None):
    # Build a dialog to edit the current character information
    edit_character_dialog = CharacterDialog(engine, character=character)
    edit_character_dialog.exec()

    # Validate dialog output
    if not edit_character_dialog.success:
        return

    # Check that the name is sensible
    character_name = edit_character_dialog.get_character_name()
    if not character_name[:1].isalpha() or character_name == "History" or character_name == "Search" or character_name == "Outputs":
        return None

    # Add the character in our engine
    if character is None:
        character = Character(name=character_name, categories=edit_character_dialog.categories)
        engine.add_character(character)
    else:
        new_character = Character(name=character_name, categories=edit_character_dialog.categories)
        new_character.unique_id = character.unique_id
        engine.edit_character(new_character)
        character = new_character

    return character


def delete_character(engine: 'LitRPGToolsEngine', character: Character):
    # TODO: Some sort of validation if this is okay?
    engine.delete_character(character)
