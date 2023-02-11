import os
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QTabWidget, QMessageBox

from new.data import Character, Category
from new.ui.desktop import category_components, character_components
from new.ui.desktop.character_components import CharacterTab
from new.ui.desktop.historic_components import HistoryTab
from new.ui.desktop.output_components import OutputsTab
from new.ui.desktop.search_components import SearchTab

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication
    from new.main import LitRPGToolsEngine


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

        # Core tabbed pane, each tab is responsible for its own content
        self.__tabbed_view = QTabWidget()
        self.__tabbed_view.currentChanged.connect(self.__handle_current_tab_changed_callback)
        self.__tabbed_view.setContentsMargins(0, 0, 0, 0)

        # Default tabs
        self.__historic_tab = HistoryTab(self, self.__engine)
        self.__search_tab = SearchTab(self, self.__engine)
        self.__outputs_tab = OutputsTab(self, self.__engine)

        # Additional tabs - these are character specific
        self.__tabs_cache = OrderedDict()

        # Tab bar props
        self.__tabbed_view.tabBar().tabBarClicked.connect(self.__handle_tab_clicked_callback)
        self.__tabbed_view.tabBar().tabMoved.connect(self.__handle_tab_moved_callback)

        # Layout
        self.setCentralWidget(self.__tabbed_view)

        # Handle autosaves
        self.check_for_autosave()

        # Force update
        self.draw()

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
        self.__add_character_menu_action.triggered.connect(self.__handle_character_creation_callback)

        self.__edit_character_menu_action = self.__character_menu.addMenu("Edit")

        self.__delete_character_menu_action = self.__character_menu.addMenu("Delete")

    def __setup_category_menu(self):
        self.__category_menu = self.__menu_bar.addMenu("Categories")

        self.__add_category_menu_action = self.__category_menu.addAction("Add")
        self.__add_category_menu_action.triggered.connect(self.__handle_category_creation_callback)

        self.__edit_category_menu_action = self.__category_menu.addMenu("Edit")

        self.__delete_category_menu_action = self.__category_menu.addMenu("Delete")

    def __handle_current_tab_changed_callback(self):
        tabbed_widget = self.__tabbed_view.currentWidget()
        if tabbed_widget is None:
            return
        tabbed_widget.draw()

    def __handle_tab_clicked_callback(self, index):
        if index > 2:
            self.__tabbed_view.tabBar().setMovable(True)
        else:
            self.__tabbed_view.tabBar().setMovable(False)

    def __handle_tab_moved_callback(self, target_index, source_index):
        if target_index < 3:
            with QSignalBlocker(self.__tabbed_view.tabBar()) as blocker:
                self.__tabbed_view.tabBar().moveTab(source_index, target_index)

        elif source_index > 1 and target_index > 1:
            self.__engine.move_character_id_by_index_to_index(source_index - 3, target_index - 3)

        else:
            a = 1

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

    def __handle_character_creation_callback(self):
        character = character_components.add_or_edit_character(self.__engine, None)
        if character is not None:
            self.draw()

    def __handle_character_edit_callback(self, character: Character):
        character = character_components.add_or_edit_character(self.__engine, character)
        current_tab_index = self.__tabbed_view.currentIndex()
        current_tab_text = self.__tabbed_view.tabText(current_tab_index)
        if current_tab_text == character.name:
            self.__tabbed_view.currentWidget().draw()

    def __handle_character_delete_callback(self, character: Character):
        character_components.delete_character(self.__engine, character)
        self.draw()

    def __handle_category_creation_callback(self):
        category = category_components.add_or_edit_category(self.__engine, None)
        if category is not None:
            self.__draw_submenus()
        # No need to update as our current implementation implies that nothing will know about this category yet...

    def __handle_category_edit_callback(self, category: Category):
        category_components.add_or_edit_category(self.__engine, category)
        self.draw()  # Broad call here as we don't know if this category is currently being displayed...

    def __handle_category_delete_callback(self, category: Category):
        category_components.delete_category(self.__engine, category)
        self.draw()  # Broad call here as we don't know if this category is currently being displayed...

    def check_for_autosave(self):
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

    def draw(self):
        # Update our menus
        self.__draw_submenus()

        # Update the current tab
        current_tab_index = self.__tabbed_view.currentIndex()
        current_tab_text = self.__tabbed_view.tabText(current_tab_index)

        # Block notifications
        self.__tabbed_view.blockSignals(True)

        # Refresh our tabs and store them in a list for comparison
        self.__tabbed_view.clear()
        self.__tabbed_view.addTab(self.__historic_tab, "History")
        self.__tabbed_view.addTab(self.__search_tab, "Search")
        self.__tabbed_view.addTab(self.__outputs_tab, "Outputs")
        character_ids = self.__engine.get_character_ids()
        for character_id in character_ids:
            character = self.__engine.get_character_by_id(character_id)

            # Retrieve cached tab and add to tabs
            if character_id in self.__tabs_cache:
                tab = self.__tabs_cache[character_id]
            else:
                tab = CharacterTab(self, self.__engine, character_id)
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
        tab_list = ["History", "Search", "Outputs", self.__tabs_cache.keys()]
        if current_tab_text in tab_list:
            index = tab_list.index(current_tab_text)
            self.__tabbed_view.setCurrentIndex(index)

        # Return signals
        self.__tabbed_view.blockSignals(False)

        # defer update to tab
        w = self.__tabbed_view.currentWidget()
        if w is not None:
            w.draw()

    def __draw_submenus(self):
        self.__draw_character_submenu()
        self.__draw_category_submenu()

    def __draw_character_submenu(self):
        characters = self.__engine.get_characters()
        self.__edit_character_menu_action.clear()
        self.__delete_character_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for character in characters:
            action = self.__edit_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(self.__handle_character_edit_callback, character))
            action = self.__delete_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(self.__handle_character_delete_callback, character))

    def __draw_category_submenu(self):
        categories = self.__engine.get_categories()
        self.__edit_category_menu_action.clear()
        self.__delete_category_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for category in categories:
            action = self.__edit_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(self.__handle_category_edit_callback, category))
            action = self.__delete_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(self.__handle_category_delete_callback, category))
