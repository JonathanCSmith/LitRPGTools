from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

import pyperclip
from PyQt6.QtCore import Qt, QSignalBlocker
from PyQt6.QtGui import QPalette, QColor, QAction, QResizeEvent, QMoveEvent
from PyQt6.QtWidgets import QMainWindow, QTabWidget, QMessageBox, QProgressDialog, QMenu

from desktop import character_components, category_components
from desktop.character_components import CharacterTab
from desktop.custom_generic_components import Content
from desktop.historic_components import HistoryTab
from desktop.output_components import OutputsTab
from desktop.search_components import SearchTab
from progress_bar import LitRPGToolsProgressUpdater

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QApplication
    from desktop.runtime import DesktopRuntime


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


class DesktopGUI(QMainWindow, Content):
    def __init__(self, app: 'QApplication', runtime: 'DesktopRuntime'):
        super(DesktopGUI, self).__init__()
        self.runtime = runtime
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
        self.setWindowTitle("LitRPGTools")

        # Display state
        if self.runtime.session.main_geometry is None:
            self.setMinimumSize(800, 600)
        else:
            self.restoreGeometry(self.runtime.session.main_geometry)

        if self.runtime.session.main_state:
            self.showMaximized()

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
        self.__tabs_cache: [str, CharacterTab] = OrderedDict()

        # Tab bar props
        self.__tabbed_view.tabBar().tabBarClicked.connect(self.__handle_tab_clicked_callback)
        self.__tabbed_view.tabBar().tabMoved.connect(self.__handle_tab_moved_callback)
        self.__tabbed_view.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.__tabbed_view.tabBar().customContextMenuRequested.connect(self.__handle_tab_right_clicked_callback)

        # Layout
        self.setCentralWidget(self.__tabbed_view)

    def __setup_menu(self):
        self.__menu_bar = self.menuBar()

        self.__setup_main_menu()
        self.__setup_character_menu()
        self.__setup_category_menu()

    def __setup_main_menu(self):
        self.__main_menu = self.__menu_bar.addMenu("Main")

        self.__save_menu_action = self.__main_menu.addAction("Save")
        self.__save_menu_action.triggered.connect(self.runtime.save_state)
        self.__save_menu_action.setShortcut("Ctrl+s")

        self.__save_as_menu_action = self.__main_menu.addAction("Save As")
        self.__save_as_menu_action.triggered.connect(partial(self.runtime.save_state, force=True))

        self.__load_menu_action = self.__main_menu.addAction("Load")
        self.__load_menu_action.triggered.connect(self.runtime.load_state)
        self.__load_menu_action.setShortcut("Ctrl+o")

        self.__load_gsheet_credentials_menu_action = self.__main_menu.addAction("Load GSheet Credentials")
        self.__load_gsheet_credentials_menu_action.triggered.connect(self.runtime.load_gsheets_credentials)

        self.__output_to_gsheets_menu_action = self.__main_menu.addAction("Output to GSheets")
        self.__output_to_gsheets_menu_action.triggered.connect(self.runtime.output_to_gsheets)
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

    def fill_content(self):
        # Any entrant to this function is ALWAYS new data
        self.clear_content()

        # Draw submenus
        self.__draw_submenus()

        # Construct our tabbed view
        self.__tabbed_view.blockSignals(True)

        # Refresh our tabs and store them in a cache
        self.__tabbed_view.addTab(self.__historic_tab, "History")
        self.__tabbed_view.addTab(self.__search_tab, "Search")
        self.__tabbed_view.addTab(self.__outputs_tab, "Outputs")
        character_ids = self.runtime.data_manager.get_character_ids()
        for character_id in character_ids:
            character = self.runtime.data_manager.get_character_by_id(character_id)
            character_tab = CharacterTab(self, character_id)
            self.__tabs_cache[character_id] = character_tab
            self.__tabbed_view.addTab(character_tab, character.name)

        # Return signals
        self.__tabbed_view.blockSignals(False)

        # inform focused tab
        w = self.__tabbed_view.currentWidget()
        if w is not None and isinstance(w, Content):
            w.fill_content()

    def __draw_submenus(self):
        self.__draw_character_submenu()
        self.__draw_category_submenu()

    def __draw_character_submenu(self):
        characters = self.runtime.data_manager.get_characters()
        self.__edit_character_menu_action.clear()
        self.__delete_character_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for character in characters:
            action = self.__edit_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(self.__handle_character_edit_callback, character.unique_id))
            action = self.__delete_character_menu_action.addAction(character.name)
            action.triggered.connect(partial(self.__handle_character_delete_callback, character.unique_id))

    def __draw_category_submenu(self):
        categories = self.runtime.data_manager.get_categories()
        self.__edit_category_menu_action.clear()
        self.__delete_category_menu_action.clear()

        # Loop through available characters and add actions for their characters specifically
        for category in categories:
            action = self.__edit_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(self.__handle_category_edit_callback, category.unique_id))
            action = self.__delete_category_menu_action.addAction(category.name)
            action.triggered.connect(partial(self.__handle_category_delete_callback, category.unique_id))

    def clear_content(self):
        self.blockSignals(True)
        self.__historic_tab.clear_content()
        self.__search_tab.clear_content()
        self.__outputs_tab.clear_content()
        self.__tabbed_view.clear()

        # Clear our tabs cache
        for character_id, tab in self.__tabs_cache.items():
            tab.deleteLater()
        self.blockSignals(False)

    def moveEvent(self, event: QMoveEvent) -> None:
        self.runtime.set_window_properties(self.saveGeometry(), self.windowState().value == 2)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.runtime.set_window_properties(self.saveGeometry(), self.windowState().value == 2)

    def closeEvent(self, a0):
        result = QMessageBox.question(self, "Are you sure?", "Do you want to save before you exit?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.runtime.save_state()
        self.runtime.delete_autosave()

    def save_clipboard_item(self, key: str, value: str):
        self.clipboard[key] = value

    def get_clipboard_item(self, key: str):
        if key in self.clipboard:
            return self.clipboard[key]
        return None

    def copy_id_to_clipboard(self, entry_id):
        root_entry_id = self.runtime.data_manager.get_root_entry_id_in_series(entry_id)
        value = "$${ID:" + root_entry_id + ":ID}$$"
        pyperclip.copy(value)
        self.save_clipboard_item("ENTRY_ID", value)

    def copy_character_to_clipboard(self, index):
        tab = self.__tabbed_view.widget(index)
        value = "$${CHAR:" + tab.character_id + ":CHAR}$$"
        pyperclip.copy(value)
        self.save_clipboard_item("CHARACTER_ID", value)

    def create_entry_summary_string(self, entry_id: str, output_index=None) -> str:
        entry = self.runtime.data_manager.get_entry_by_id(entry_id)
        entry_index = self.runtime.data_manager.get_entry_index_in_history(entry_id)
        category = self.runtime.data_manager.get_category_by_id(entry.category_id)
        character = self.runtime.data_manager.get_character_by_id(entry.character_id)

        # Display string is dependent on lineage
        if entry.parent_id is None:
            template_string = category.creation_text
        else:
            template_string = category.update_text

        # Format our string
        body_string = template_string.format(*entry.data)

        # Conditional output for outputs (which need their output index as well
        if output_index is None:
            return "[" + str(entry_index) + "] (" + character.name + "): " + body_string
        else:
            return "[" + str(entry_index) + " (" + str(output_index) + ")] (" + character.name + "): " + body_string

    def create_category_summary_string(self, category_id: str) -> str:
        category = self.runtime.data_manager.get_category_by_id(category_id)
        return "[Category]: " + category.name

    def __handle_tab_right_clicked_callback(self, pos):
        tab_index = self.__tabbed_view.tabBar().tabAt(pos)
        if tab_index < 3:
            return

        context_menu = QMenu(self)

        # Create actions for the context menu
        copy_character_id_to_clipboard_action = QAction("Copy Current Character ID", self)
        copy_character_id_to_clipboard_action.triggered.connect(partial(self.copy_character_to_clipboard, tab_index))

        # Add actions to the context menu
        context_menu.addAction(copy_character_id_to_clipboard_action)

        # Show the context menu at the mouse position
        context_menu.exec(self.mapToGlobal(pos))

    def __handle_current_tab_changed_callback(self):
        tabbed_widget = self.__tabbed_view.currentWidget()
        if tabbed_widget is not None and isinstance(tabbed_widget, Content):
            tabbed_widget.fill_content()

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
            self.runtime.data_manager.move_character_id_by_index_to_index(source_index - 3, target_index - 3)

    def __handle_character_creation_callback(self):
        character = character_components.add_or_edit_character(self, None)

        # Redraw our menus, easier just to brute force it
        self.__draw_character_submenu()

        # Add our character tab
        character_tab = CharacterTab(self, character.unique_id)
        self.__tabs_cache[character.unique_id] = character_tab
        self.__tabbed_view.addTab(character_tab, character.name)

    def __handle_character_edit_callback(self, character_id: str):
        character_components.add_or_edit_character(self, character_id)

        # Redraw our menus, easier just to brute force it
        self.__draw_character_submenu()

        # If this character is the current tab, redraw
        character_tab = self.__tabs_cache[character_id]
        tab_index = self.__tabbed_view.indexOf(character_tab)
        character = self.runtime.data_manager.get_character_by_id(character_id)
        self.__tabbed_view.setTabText(tab_index, character.name)
        if self.__tabbed_view.currentIndex() == tab_index:
            character_tab.fill_content()

    def __handle_character_delete_callback(self, character_id: str):
        character_components.delete_character(self.runtime.data_manager, character_id)

        # Redraw our menus, easier just to brute force it
        self.__draw_character_submenu()

        # Remove & Delete tab
        character_tab = self.__tabs_cache[character_id]
        tab_index = self.__tabbed_view.indexOf(character_tab)
        self.__tabbed_view.removeTab(tab_index)
        character_tab.deleteLater()

    def __handle_category_creation_callback(self):
        category = category_components.add_or_edit_category(self, None)

        # Redraw our menus, easier just to brute force it
        self.__draw_category_submenu()
        # Note, there is no need to redraw characters as they need to have their categories explicitly adjusted to include the new category

    def __handle_category_edit_callback(self, category_id: str):
        category_components.add_or_edit_category(self, category_id)

        # Redraw our menus, easier just to brute force it
        self.__draw_category_submenu()

        # Check if a character tab is being displayed and inform it of a potential update
        tab_index = self.__tabbed_view.currentIndex()
        if tab_index <= 2:
            return

        character_tab = self.__tabbed_view.currentWidget()
        character = self.runtime.data_manager.get_character_by_id(character_tab.character_id)
        if category_id in character.categories:
            character_tab.fill_content()

    def __handle_category_delete_callback(self, category_id: str):
        category_components.delete_category(self, category_id)

        # Redraw our menus, easier just to brute force it
        self.__draw_category_submenu()

        # Check if a character tab is being displayed and inform it of a potential update
        tab_index = self.__tabbed_view.currentIndex()
        if tab_index <= 2:
            return

        character_tab = self.__tabbed_view.currentWidget()
        character = self.runtime.data_manager.get_character_by_id(character_tab.character_id)
        if category_id in character.categories:
            character_tab.fill_content()
