import os
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QTabWidget, QMessageBox, QProgressDialog

from data import Character
from progress_bar import LitRPGToolsProgressUpdater
from desktop import character_components, category_components
from desktop.character_components import CharacterTab
from desktop.historic_components import HistoryTab
from desktop.output_components import OutputsTab
from desktop.search_components import SearchTab

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication
    from main import LitRPGToolsInstance
    from session import LitRPGToolsSession


class LitRPGToolsDesktopGUIProgressUpdater(LitRPGToolsProgressUpdater):
    def __init__(self, main_gui):
        # Progress bar
        self.progress_bar = QProgressDialog("Data output in progress: ", None, 0, 1, main_gui)
        self.progress_bar.setWindowTitle("Outputting data.")
        self.progress_bar.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_bar.setValue(0)

    def set_minimum(self, value: int):
        self.progress_bar.setMinimum(0)

    def set_maximum(self, value: int):
        self.progress_bar.setMaximum(value)

    def set_current_work_done(self, value: int):
        self.progress_bar.setValue(value)

    def finish(self):
        self.progress_bar.close()


class LitRPGToolsDesktopGUI(QMainWindow):
    def __init__(self, runtime: 'LitRPGToolsInstance', session: 'LitRPGToolsSession', app: 'QApplication'):
        super(LitRPGToolsDesktopGUI, self).__init__()
        self.instance = runtime
        self.session = session
        self.data_manager = session.data_manager
        self.__app = app

        # Clipboard
        self.clipboard = dict()

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
        self.__historic_tab = HistoryTab(self)
        self.__search_tab = SearchTab(self)
        self.__outputs_tab = OutputsTab(self)

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

    def save_clipboard_item(self, key: str, value: str):
        self.clipboard[key] = value

    def get_clipboard_item(self, key: str):
        if key in self.clipboard:
            return self.clipboard[key]
        return None

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
            self.data_manager.move_character_id_by_index_to_index(source_index - 3, target_index - 3)

        else:
            a = 1

    def __handle_save_callback(self):
        if not self.session.has_save_path():
            self.__handle_save_as_callback()
        else:
            self.session.save_state()

    def __handle_save_as_callback(self):
        results = QFileDialog.getSaveFileName(self, "Save File", "*.litrpg", filter="*.litrpg")
        if results[0] == "":
            return

        # Split the directory and delegate parts out
        folder, file = os.path.split(os.path.abspath(results[0]))
        self.instance.set_data_directory(folder)
        self.session.set_save_information(file)
        self.session.save_state()

    def __handle_load_callback(self):
        results = QFileDialog.getOpenFileName(self, "Load File", filter="*.litrpg")
        if results[0] == "":
            return

        # Split the directory and delegate parts out
        folder, file = os.path.split(os.path.abspath(results[0]))
        self.instance.set_data_directory(folder)
        self.session.set_save_information(file)
        self.session.load_state()
        self.draw()

    def __handle_load_gsheet_credentials_callback(self):
        results = QFileDialog.getOpenFileName(self, 'Load GSheets Credentials File', filter="*.json")
        if results[0] == "" or not os.path.exists(results[0]):
            return
        self.data_manager.gsheet_credentials_path = results[0]

    def __handle_output_to_gsheets_callback(self):
        progress_bar = LitRPGToolsDesktopGUIProgressUpdater(self)
        self.session.output_to_gsheets(progress_bar)

    def __handle_character_creation_callback(self):
        character = character_components.add_or_edit_character(self, None)
        if character is not None:
            self.draw()

    def __handle_character_edit_callback(self, character: Character):
        character_components.add_or_edit_character(self, character)
        self.draw()

    def __handle_character_delete_callback(self, character: Character):
        character_components.delete_character(self.data_manager, character)
        self.draw()

    def __handle_category_creation_callback(self):
        category = category_components.add_or_edit_category(self, None)
        if category is not None:
            self.__draw_submenus()
        # No need to update as our current implementation implies that nothing will know about this category yet...

    def __handle_category_edit_callback(self, category_id: str):
        category = self.data_manager.get_category_by_id(category_id)
        category_components.add_or_edit_category(self, category)
        self.draw()  # Broad call here as we don't know if this category is currently being displayed...

    def __handle_category_delete_callback(self, category_id: str):
        category = self.data_manager.get_category_by_id(category_id)
        category_components.delete_category(self, category)
        self.draw()  # Broad call here as we don't know if this category is currently being displayed...

    def check_for_autosave(self):
        if self.session.has_autosave():
            result = QMessageBox.question(self, "Autosave Detected", "Do you wish to load the autosave? This was likely created prior to a crash...", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if result == QMessageBox.StandardButton.Yes:
                self.session.load_autosave()
            else:
                self.session.delete_autosave()

    def closeEvent(self, a0):
        result = QMessageBox.question(self, "Are you sure?", "Do you want to save before you exit?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.__handle_save_callback()
        self.session.delete_autosave()

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
        character_ids = self.data_manager.get_character_ids()
        for character_id in character_ids:
            character = self.data_manager.get_character_by_id(character_id)

            # Retrieve cached tab and add to tabs
            if character_id in self.__tabs_cache:
                tab = self.__tabs_cache[character_id]
            else:
                tab = CharacterTab(self, character_id)
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
        characters = self.data_manager.get_characters()
        self.__edit_character_menu_action.clear()
        self.__delete_character_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for character in characters:
            action = self.__edit_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(self.__handle_character_edit_callback, character))
            action = self.__delete_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(self.__handle_character_delete_callback, character))

    def __draw_category_submenu(self):
        categories = self.data_manager.get_categories()
        self.__edit_category_menu_action.clear()
        self.__delete_category_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for category in categories:
            action = self.__edit_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(self.__handle_category_edit_callback, category.unique_id))
            action = self.__delete_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(self.__handle_category_delete_callback, category.unique_id))
