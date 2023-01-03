import os
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QWidget, QVBoxLayout, QComboBox, QListWidget, QAbstractItemView, QPushButton, QListWidgetItem, QLabel, QTabWidget, QCheckBox, QMessageBox

from new.data import Character, Category, Entry
from new.ui.desktop import category_components, character_components, entry_components, output_components
from new.ui.desktop.custom_generic_components import VisibleDynamicSplitPanel
from new.ui.desktop.output_components import OutputsTab
from new.ui.desktop.tabs import SelectedTab, SearchTab, CharacterTab

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication
    from new.main import LitRPGToolsEngine


class SidebarWidget(QWidget):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(SidebarWidget, self).__init__()
        self.__parent = parent
        self.__engine = engine

        # Exposed
        self.is_viewing_history = True

        # Allow Selection of what we want to display in the sidebar
        self.__highlight_selector = QComboBox()
        self.__highlight_selector.currentTextChanged.connect(self.__handle_sidebar_focus_changed_callback)

        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # New entry button
        self.__new_entry_button = QPushButton("Create Entry at Current History Index")
        self.__new_entry_button.clicked.connect(partial(entry_components.add_entry, self.__engine, self.__parent))

        # New view button
        self.__new_view_button = QPushButton("Create View at Current History Index")
        self.__new_view_button.clicked.connect(partial(output_components.add_or_edit_output, self.__engine, self.__parent, None))

        # 'View' buttons
        self.__display_hidden_checkbox = QCheckBox("Display Hidden Entries")
        self.__display_hidden_checkbox.clicked.connect(self.__handle_display_hidden_callback)
        self.__view_hidden = self.__display_hidden_checkbox.isChecked()
        self.__view_dynamic_data_checkbox = QCheckBox("View Dynamic Data")
        self.__view_dynamic_data_checkbox.clicked.connect(self.__handle_view_dynamic_data_callback)
        self.__view_dynamic = self.__view_dynamic_data_checkbox.isChecked()

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(QLabel("Current Highlight:"))
        self.__layout.addWidget(self.__highlight_selector)
        self.__layout.addWidget(self.__active_list)
        self.__layout.addWidget(self.__new_entry_button)
        self.__layout.addWidget(self.__new_view_button)
        self.__layout.addWidget(self.__display_hidden_checkbox)
        self.__layout.addWidget(self.__view_dynamic_data_checkbox)
        self.setLayout(self.__layout)
        self.setContentsMargins(0, 0, 0, 0)

    def __handle_sidebar_focus_changed_callback(self):
        self.__parent.handle_update()

        # Set our currently selected to the end to save on some headaches or obtuse logic
        self.__active_list.setCurrentRow(self.__active_list.count() - 1)

    def __handle_sidebar_selection_changed_callback(self):
        # Block signals on the callback whilst we update so no recursion
        self.__active_list.itemSelectionChanged.disconnect(self.__handle_sidebar_selection_changed_callback)
        self.__parent.handle_update()
        self.__paint_list()
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

    def __paint_list(self):
        for i in range(self.__active_list.count()):
            colour = self.__get_list_row_colour_from_context(i)
            self.__active_list.item(i).setForeground(colour)

    def __get_list_row_colour_from_context(self, index) -> Qt.GlobalColor:
        # First check if it's our active 'head'
        if self.__engine.get_current_history_index() == index:
            return Qt.GlobalColor.blue

        # Check for a familial relationship with the currently selected
        entry_id = self.__active_list.currentItem().data(Qt.ItemDataRole.UserRole)
        familial_relatives = self.__engine.get_entry_revisions_for_id(entry_id)
        if self.__active_list.item(index).data(Qt.ItemDataRole.UserRole) in familial_relatives:
            return Qt.GlobalColor.yellow

        # Highlight based on 'selector' to green?
        output_id = self.__highlight_selector.currentData()
        entry_id = self.__engine.get_entry_id_by_history_index(index)
        if output_id is not None:
            output = self.__engine.get_output_by_id(output_id)
            if entry_id in output.members:
                return Qt.GlobalColor.green
            elif entry_id in output.ignored:
                return Qt.GlobalColor.red

        return Qt.GlobalColor.white

    def __handle_display_hidden_callback(self):
        self.__view_hidden = self.__display_hidden_checkbox.isChecked()
        self.__parent.handle_update()

    def __handle_view_dynamic_data_callback(self):
        self.__view_dynamic = self.__view_dynamic_data_checkbox.isChecked()
        self.__parent.handle_update()

    def handle_update(self):
        # Handle initial case
        if self.__highlight_selector.currentText() is None or self.__highlight_selector.currentText() == "":
            self.__fill_highlight_selector()

        # Recreate and ensure we are on the correct selection
        else:
            currently_selected = self.__highlight_selector.currentText()
            self.__fill_highlight_selector(selected=currently_selected)

        # Fill our list
        self.__fill_active_list()

    def __fill_highlight_selector(self, selected="History"):
        outputs = self.__engine.get_outputs()

        # Block signalling & clear
        self.__highlight_selector.blockSignals(True)
        self.__highlight_selector.clear()

        # Add in our default view
        self.__highlight_selector.addItem("Full History")

        # Loop through outputs and add their ids as data - also search for matches in terms of selection
        found = False
        for index, output in enumerate(outputs):
            self.__highlight_selector.addItem(output.name)
            self.__highlight_selector.setItemData(index + 1, output.unique_id, Qt.ItemDataRole.UserRole)

            # Mark that we have a match for our selected view
            if output.name == selected:
                found = True

        # Special case when a view was deleted and previously selected
        if not found:
            selected = "Full History"
        self.__highlight_selector.setCurrentText(selected)

        # Return signalling
        self.__highlight_selector.blockSignals(False)

        # Update our context flag
        self.is_viewing_history = selected == "Full History"

    def __fill_active_list(self):
        # Get the current selection
        current_selection = self.__active_list.currentRow()

        # Switch what information we populate our list with depending on the view selector
        self.__fill_list(self.__engine.get_history())
        # if self.is_viewing_history:
        #     self.__fill_list(self.__engine.get_history())
        # else:
        #     view = self.__engine.get_output_by_id(self.__highlight_selector.currentData(Qt.ItemDataRole.UserRole))
        #     self.__fill_list(view.members)

        # Handle the unique case where we added our first entry
        if current_selection == -1 and self.__engine.get_length_of_history() > 0:
            current_selection = 0

        # Force an update so our text colour can be rendered
        self.__active_list.setCurrentRow(current_selection)

    def __fill_list(self, entries):
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        for index, entry_id in enumerate(entries):
            entry = self.__engine.get_entry_by_id(entry_id)
            category = self.__engine.get_category_by_id(entry.category_id)
            character = self.__engine.get_character_by_id(entry.character_id)

            # Display string format
            if entry.parent_id is None:
                display_string = category.creation_text
            else:
                display_string = category.update_text
            display_string = self.__fill_display_string(display_string, index, character, category, entry)

            # Add the string
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)
            self.__active_list.addItem(item)
        self.__active_list.blockSignals(False)

    def __fill_display_string(self, template_string: str, index: int, character: Character, category: Category, entry: Entry):
        string_result = template_string.format(*entry.data)  # TODO! Codify some nice stuff here
        return "[" + str(index) + "] (" + character.name + "): " + string_result

    def get_currently_selected(self) -> QListWidgetItem | None:
        return self.__active_list.currentItem()

    def set_currently_selected(self, index):
        self.__active_list.setCurrentRow(index)

    def get_should_display_hidden(self):
        return self.__view_hidden

    def get_should_display_dynamic(self):
        return self.__view_dynamic


class ViewWidget(QWidget):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(ViewWidget, self).__init__()
        self.__parent = parent
        self.__engine = engine

        # Core tabbed view
        self.__tabbed_view = QTabWidget()
        self.__tabbed_view.currentChanged.connect(self.__handle_current_tab_changed_callback)

        # Default tabs
        self.__selected_tab = SelectedTab(self.__parent, self.__engine)
        self.__search_tab = SearchTab(self.__parent, self.__engine)
        self.__outputs_tab = OutputsTab(self.__parent, self.__engine)

        # Additional tabs
        self.__tabs_cache = OrderedDict()

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__tabbed_view)
        self.setLayout(self.__layout)
        self.setContentsMargins(0, 0, 0, 0)

        # Force update
        self.handle_update()

    def __handle_current_tab_changed_callback(self):
        tabbed_widget = self.__tabbed_view.currentWidget()
        if tabbed_widget is None:
            return
        tabbed_widget.handle_update()

    def handle_update(self):
        current_tab_index = self.__tabbed_view.currentIndex()
        current_tab_text = self.__tabbed_view.tabText(current_tab_index)

        # Block notifications
        self.__tabbed_view.blockSignals(True)

        # Refresh our tabs and store them in a list for comparison
        self.__tabbed_view.clear()
        self.__tabbed_view.addTab(self.__selected_tab, "Currently Selected")
        self.__tabbed_view.addTab(self.__search_tab, "Search")
        self.__tabbed_view.addTab(self.__outputs_tab, "Outputs")
        character_ids = self.__engine.get_character_ids()
        for character_id in character_ids:
            character = self.__engine.get_character_by_id(character_id)

            # Retrieve cached tab and add to tabs
            if character_id in self.__tabs_cache:
                tab = self.__tabs_cache[character_id]
            else:
                tab = CharacterTab(self.__parent, self.__engine, character_id)
                self.__tabs_cache[character_id] = tab
            self.__tabbed_view.addTab(tab, character.name)

        # Remove redundant cached items
        items_to_delete = []
        for character_id in self.__tabs_cache.keys():
            if character_id not in character_ids:
                items_to_delete.append(character_id)
        for item in items_to_delete:
            self.__tabs_cache[item].deleteLater()
            del self.__tabs_cache[item]

        # Return to selected if possible
        tab_list = ["Currently Selected", "Search", "Outputs"]
        tab_list.append(self.__tabs_cache.keys())
        if current_tab_text in tab_list:
            index = tab_list.index(current_tab_text)
            self.__tabbed_view.setCurrentIndex(index)

        # Return signals
        self.__tabbed_view.blockSignals(False)

        # defer update to tab
        w = self.__tabbed_view.currentWidget()
        if w is not None:
            w.handle_update()


class LitRPGToolsDesktopGUI(QMainWindow):
    def __init__(self, engine: 'LitRPGToolsEngine', app: 'QApplication'):
        super(LitRPGToolsDesktopGUI, self).__init__()
        self.__engine = engine
        self.__app = app

        # Theme
        # Force the style to be the same on all OSs:
        self.__app.setStyle("Fusion")

        # Now use a palette to switch to dark colors:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.__app.setPalette(palette)

        # General
        self.setMinimumSize(800, 600)
        self.showMaximized()
        self.setWindowTitle("LitRPGTools")

        # Main menu
        self.__setup_menu()

        # Core elements
        self.__sidebar_widget = SidebarWidget(self, self.__engine)
        self.__view_widget = ViewWidget(self, self.__engine)

        # Core display
        self.__main_widget = VisibleDynamicSplitPanel(Qt.Orientation.Horizontal)
        self.__main_widget.addWidget(self.__sidebar_widget)
        self.__main_widget.addWidget(self.__view_widget)
        self.__main_widget.setStretchFactor(0, 20)
        self.__main_widget.setStretchFactor(1, 200)
        self.__main_widget.setSizes([200, 1000])
        self.__main_widget.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.__main_widget)

        # Handle autosaves
        self.check_for_autosaves()

        # Force update
        self.handle_update()

    def __setup_menu(self):
        self.__menu_bar = self.menuBar()

        self.__setup_main_menu()
        self.__setup_character_menu()
        self.__setup_category_menu()

    def __setup_main_menu(self):
        self.__main_menu = self.__menu_bar.addMenu("Main")

        self.__save_menu_action = self.__main_menu.addAction("Save")
        self.__save_menu_action.triggered.connect(self.__handle_save_callback)
        self.__save_menu_action.setShortcut("Ctrl+s")

        self.__save_as_menu_action = self.__main_menu.addAction("Save As")
        self.__save_as_menu_action.triggered.connect(self.__handle_save_as_callback)

        self.__load_menu_action = self.__main_menu.addAction("Load")
        self.__load_menu_action.triggered.connect(self.__handle_load_callback)
        self.__load_menu_action.setShortcut("Ctrl+o")

        self.__load_gsheet_credentials_menu_action = self.__main_menu.addAction("Load GSheet Credentials")
        self.__load_gsheet_credentials_menu_action.triggered.connect(self.__handle_load_gsheet_credentials_callback)

        self.__output_to_gsheets_menu_action = self.__main_menu.addAction("Output to GSheets")
        self.__output_to_gsheets_menu_action.triggered.connect(self.__handle_output_to_gsheets_callback)
        self.__output_to_gsheets_menu_action.setShortcut("Ctrl+p")

    def __setup_character_menu(self):
        self.__character_menu = self.__menu_bar.addMenu("Characters")

        self.__add_character_menu_action = self.__character_menu.addAction("Add")
        self.__add_character_menu_action.triggered.connect(partial(character_components.add_or_edit_character, self.__engine, self, None))

        self.__edit_character_menu_action = self.__character_menu.addMenu("Edit")

        self.__delete_character_menu_action = self.__character_menu.addMenu("Delete")

    def __setup_category_menu(self):
        self.__category_menu = self.__menu_bar.addMenu("Categories")

        self.__add_category_menu_action = self.__category_menu.addAction("Add")
        self.__add_category_menu_action.triggered.connect(partial(category_components.add_or_edit_category, self.__engine, self, None))

        self.__edit_category_menu_action = self.__category_menu.addMenu("Edit")

        self.__delete_category_menu_action = self.__category_menu.addMenu("Delete")

    def __handle_save_callback(self):
        if self.__engine.file_save_path is None or not os.path.isfile(self.__engine.file_save_path):
            self.__handle_save_as_callback()
        else:
            self.__engine.save()

    def __handle_save_as_callback(self):
        results = QFileDialog.getSaveFileName(self, "Save File", "*.litrpg", filter="*.litrpg")
        if results[0] == "":
            return

        self.__engine.file_save_path = results[0]
        self.__engine.save()

    def __handle_load_callback(self):
        results = QFileDialog.getOpenFileName(self, "Load File", filter="*.litrpg")
        if results[0] == "":
            return

        self.__engine.file_save_path = results[0]
        self.__engine.load()

    def __handle_load_gsheet_credentials_callback(self):
        results = QFileDialog.getOpenFileName(self, 'Load GSheets Credentials File', filter="*.json")
        if results[0] == "":
            return

        self.__engine.load_gsheets_credentials(results[0])

    def __handle_output_to_gsheets_callback(self):
        # Attempt a save before outputting
        self.__handle_save_callback()
        self.__engine.output_to_gsheets()

    def check_for_autosaves(self):
        if self.__engine.has_autosave():
            result = QMessageBox.question(self, "Autosave Detected", "Do you wish to load the autosave? This was likely created prior to a crash...", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if result == QMessageBox.StandardButton.Yes:
                self.__engine.load_autosave()
            else:
                self.__engine.delete_autosave()

    def closeEvent(self, a0):
        result = QMessageBox.question(self, "Are you sure?", "Do you want to save before you exit?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.__handle_save_callback()
        self.__engine.delete_autosave()

    def handle_update(self):
        # TODO get index or forced index

        self.__handle_update_submenus()
        self.__sidebar_widget.handle_update()
        self.__view_widget.handle_update()

        # TODO: Display hidden toggle behaviours

    def __handle_update_submenus(self):
        self.__handle_update_character_submenu()
        self.__handle_update_category_submenu()

    def __handle_update_character_submenu(self):
        characters = self.__engine.get_characters()
        self.__edit_character_menu_action.clear()
        self.__delete_character_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for character in characters:
            action = self.__edit_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(character_components.add_or_edit_character, self.__engine, self, character))
            action = self.__delete_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(character_components.delete_character, self.__engine, self, character))

    def __handle_update_category_submenu(self):
        categories = self.__engine.get_categories()
        self.__edit_category_menu_action.clear()
        self.__delete_category_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for category in categories:
            action = self.__edit_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(category_components.add_or_edit_category, self.__engine, self, category))
            action = self.__delete_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(category_components.delete_category, self.__engine, self, category))

    def get_currently_selected(self) -> QListWidgetItem | None:
        return self.__sidebar_widget.get_currently_selected()

    def set_curently_selected(self, index: int):
        self.__sidebar_widget.set_currently_selected(index)

    def get_should_display_hidden(self):
        return self.__sidebar_widget.get_should_display_hidden()

    def get_should_display_dynamic(self):
        return self.__sidebar_widget.get_should_display_dynamic()
