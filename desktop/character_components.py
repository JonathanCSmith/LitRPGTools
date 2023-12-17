from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING, Dict

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtWidgets import QDialog, QLineEdit, QTableWidget, QPushButton, QFormLayout, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox, QTabWidget, QVBoxLayout, QWidget, QCheckBox, QLabel, QHBoxLayout, QScrollArea

from data.models import Character
from desktop.category_components import CategoryTab
from desktop.custom_generic_components import add_checkbox_in_table_at, MemoryModalDialog, Content

if TYPE_CHECKING:
    from data.data_manager import DataManager
    from desktop.guis import DesktopGUI


"""
TODO: Change pointer to entry_id
TODO: No entry storage
TODO: No caching. fill_content == wipe!
TODO: No partials
TODO: References to component.whatever (i.e. category_components.create) should be by id!
TODO: Most functions should use ids not whole data model objs
"""


class CharacterTab(QWidget, Content):
    def __init__(self, root_gui: 'DesktopGUI', character_id: str):
        super(CharacterTab, self).__init__()
        self.root_gui = root_gui
        self.character_id = character_id

        # Content
        self.__tabbed_view = QTabWidget()
        self.__tabbed_view.currentChanged.connect(self.__handle_current_tab_changed_callback)

        # Additional tabs
        self.__character_configuration_tab = CharacterConfigurationTab(self.root_gui, self)
        self.__dynamic_data_tab = DynamicDataTab(self.root_gui, self)
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

    def fill_content(self):
        self.clear_content()

        # Current tab
        current_tab_index = self.__tabbed_view.currentIndex()
        current_tab_text = self.__tabbed_view.tabText(current_tab_index)

        self.__tabbed_view.blockSignals(True)

        # Fixed tabs
        self.__tabbed_view.addTab(self.__character_configuration_tab, "Character Categories")
        self.__tabbed_view.addTab(self.__dynamic_data_tab, "Dynamic Data Store")

        # Dynamic tabs
        character = self.root_gui.runtime.data_manager.get_character_by_id(self.character_id)
        for category_id in character.categories:
            category = self.root_gui.runtime.data_manager.get_category_by_id(category_id)
            category_tab = CategoryTab(self.root_gui, self, category_id)
            self.__tabs_cache[category_id] = category_tab
            self.__tabbed_view.addTab(category_tab, category.name)

        # Return to selected
        keys = ["Character Categories", "Dynamic Data Store", self.__tabs_cache.keys()]
        if current_tab_text in keys:
            index = keys.index(current_tab_text)
            self.__tabbed_view.setCurrentIndex(index)

        self.__tabbed_view.blockSignals(False)

        # inform focused tab
        w = self.__tabbed_view.currentWidget()
        if w is not None and isinstance(w, Content):
            w.fill_content()

    def clear_content(self):
        self.blockSignals(True)
        self.__character_configuration_tab.clear_content()
        self.__dynamic_data_tab.clear_content()
        self.__tabbed_view.clear()

        # Clear out old tabs
        for category_id, tab in self.__tabs_cache.items():
            tab.deleteLater()
        self.blockSignals(False)

    def __handle_current_tab_changed_callback(self):
        tabbed_widget = self.__tabbed_view.currentWidget()
        if tabbed_widget is not None and isinstance(tabbed_widget, Content):
            tabbed_widget.fill_content()

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
            self.root_gui.runtime.data_manager.move_category_id_by_index_to_index(self.character_id, source_index - 2, target_index - 2)


class CharacterConfigurationTab(QWidget, Content):
    def __init__(self, root_gui: 'DesktopGUI', character_tab: CharacterTab):
        super().__init__()
        self.root_gui = root_gui
        self.character_tab = character_tab

        # TODO: May need a scroll area - see below if so

        # Form layout
        self.__layout = QFormLayout()
        self.__layout.addRow("Categories:", QLabel("Active?"))
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def fill_content(self):
        self.clear_content()

        character = self.root_gui.runtime.data_manager.get_character_by_id(self.character_tab.character_id)
        categories = self.root_gui.runtime.data_manager.get_categories()
        for category in categories:
            check_box = QCheckBox()
            state = category.unique_id in character.categories
            check_box.setChecked(state)
            check_box.clicked.connect(partial(self.__handle_category_box_callback, category.unique_id, state))
            self.__layout.addRow(category.name, check_box)

    def clear_content(self):
        self.blockSignals(True)
        for index in range(self.__layout.rowCount()):
            self.__layout.removeRow(1)
        self.blockSignals(False)

    def __handle_category_box_callback(self, category_id: str, current_state: bool):
        character = self.root_gui.runtime.data_manager.get_character_by_id(self.character_tab.character_id)
        if current_state:
            character.categories.remove(category_id)
        else:
            character.categories.append(category_id)
        self.root_gui.runtime.data_manager.edit_character(character)

        # Call parent so that the tabs can be updated
        self.character_tab.clear_content()
        self.character_tab.fill_content()


class DynamicDataTab(QWidget, Content):
    def __init__(self, root_gui: 'DesktopGUI', character_tab: CharacterTab):
        super().__init__()
        self.root_gui = root_gui
        self.character_tab = character_tab

        # Toggle button
        self.__toggle_private = False
        self.__toggle_private_button = QCheckBox()
        self.__toggle_private_button.setChecked(False)
        self.__toggle_private_button.clicked.connect(self.__handle_toggle_private_callback)
        self.__toggle_private_layout = QHBoxLayout()
        self.__toggle_private_layout.addWidget(QLabel("Show Private:"))
        self.__toggle_private_layout.addWidget(self.__toggle_private_button)
        self.__toggle_private_layout.addStretch()
        # self.__toggle_private_layout.setContentsMargins(0, 0, 0, 0)
        self.__toggle_private_widget = QWidget()
        self.__toggle_private_widget.setLayout(self.__toggle_private_layout)
        self.__toggle_private_widget.setContentsMargins(0, 0, 0, 0)

        # Layout
        self.__form = QFormLayout()
        self.__form.addRow("Dynamic Data Key", QLabel("Dynamic Data Value"))
        self.__form_widget = QWidget()
        self.__form_widget.setLayout(self.__form)
        self.__scroll = QScrollArea()
        self.__scroll.setWidget(self.__form_widget)
        self.__scroll.setWidgetResizable(True)
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__scroll)
        self.__layout.addWidget(self.__toggle_private_widget)
        self.setLayout(self.__layout)

    def fill_content(self):
        self.clear_content()

        dynamic_data = self.root_gui.runtime.data_manager.get_dynamic_data_for_current_index_and_character_id(self.character_tab.character_id, self.__toggle_private)
        for k, v in dynamic_data.items():
            self.__form.addRow(k, QLabel(str(v)))

    def clear_content(self):
        self.blockSignals(True)
        for row in range(self.__form.rowCount()):
            self.__form.removeRow(1)
        self.blockSignals(False)

    def __handle_toggle_private_callback(self):
        self.__toggle_private = self.__toggle_private_button.isChecked()
        self.fill_content()


class CharacterDialog(MemoryModalDialog):
    def __init__(self, gui: 'DesktopGUI', character=None):
        super(CharacterDialog, self).__init__(gui=gui, parent=gui.parent())
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
        categories = self.desktop_gui.runtime.data_manager.get_categories()
        self.__character_categories_table.setRowCount(len(categories))
        for i, category in enumerate(categories):
            self.__character_categories_table.setItem(i, 0, QTableWidgetItem(category.name))

            # Check whether or not this character cares about this state at all
            if self.__character is None:
                state = False
            else:
                state = category.unique_id in self.__character.categories

            # Add a checkbox to allow the user to register the interest of this character in
            add_checkbox_in_table_at(self.__character_categories_table, i, state=state, callback=partial(self.__handle_toggle_category_callback, category.unique_id))

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
    def __init__(self, characters: Dict[str, Character]):
        super().__init__()
        self.success = False
        self.character_id = None

        # Character selector
        self.__character_selector = QComboBox()
        self.__character_selector.addItem("Please Select A Character")

        # Fill in our character data
        row_count = 0
        for character_id, character in characters.items():
            self.__character_selector.addItem(character.name)
            row_count += 1
            self.__character_selector.setItemData(row_count, character.unique_id, Qt.ItemDataRole.UserRole)

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


def add_or_edit_character(root_gui: 'DesktopGUI', character_id: str | None):
    # Build a dialog to edit the current character information
    character = root_gui.runtime.data_manager.get_character_by_id(character_id)
    edit_character_dialog = CharacterDialog(root_gui, character=character)
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
        root_gui.runtime.data_manager.add_character(character)
    else:
        new_character = Character(name=character_name, categories=edit_character_dialog.categories)
        new_character.unique_id = character.unique_id
        root_gui.runtime.data_manager.edit_character(new_character)
        character = new_character

    return character


def delete_character(data_manager: 'DataManager', character_id: str):
    # TODO: Some sort of validation if this is okay?
    data_manager.delete_character(character_id)
