from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QAction
from PyQt6.QtWidgets import QMainWindow, QListWidget, QAbstractItemView, QPushButton, QVBoxLayout, QWidget, QTabWidget, QFormLayout, QMenu, QHBoxLayout, QLineEdit, QLabel, QCheckBox, QScrollArea

from data.entries import Entry
from gui.category_dialogs import CategoryDialog, EditCategoryDialog, CategoryAssignmentDialog
from gui.character_dialogs import CharacterDialog, CharacterSelectDialog
from gui.common_widgets import VisibleDynamicSplitPanel
from gui.entry_dialogs import CreateEntryDialog
from gui.gui_utils import handle_update_later_entries, create_edit_dialog, create_update_dialog
from gui.sheets_dialogs import TagDialog
from gui.spell_check_plain_text import SpellTextEdit

if TYPE_CHECKING:
    from main import LitRPGTools


class SelectedView(QWidget):
    def __init__(self, engine: 'LitRPGTools', parent):
        super(SelectedView, self).__init__()
        self.engine = engine
        self.parent = parent

        # Cache
        self.data = list()
        self.currently_selected = None

        # Fixed button
        self.should_print_to_output = None
        self.should_print_to_history = None
        self.new_entry_button = None
        self.done_button = None

        # Set the layout
        self.form_layout = QFormLayout()
        self.setLayout(self.form_layout)

    def get_data(self):
        # Gather our output data
        data_out = list()
        for item in self.data:
            if item is None:
                data_out.append("")
            elif isinstance(item, QLineEdit):
                data_out.append(item.text())
            else:
                data_out.append(item.toPlainText())

        return data_out

    def handle_submit_button(self):
        data_out = self.get_data()
        current_selection = self.parent.history_list.currentRow()
        self.engine.update_existing_entry_values(self.currently_selected.get_unique_key(), data_out, should_print_to_output=self.should_print_to_output.isChecked(), should_print_to_history=self.should_print_to_history.isChecked())

        # Check if this is the most recent entry
        current_key = self.currently_selected.get_unique_key()
        handle_update_later_entries(self.engine, current_key)
        self.parent.handle_update(currently_selected=current_selection)

    def handle_update_button(self):
        data_out = self.get_data()

        # Get the 'latest' entry in the series up to our current 'head'.
        absolute_root_key = self.engine.get_absolute_parent(self.currently_selected.get_unique_key())
        if absolute_root_key is None:
            target_key = self.engine.get_most_recent_revision_for_root_entry_key(self.currently_selected.get_unique_key())
        else:
            target_key = self.engine.get_most_recent_revision_for_root_entry_key(absolute_root_key)

        # Check for diffs - on no difference we ignore this action
        target_entry = self.engine.get_entry(target_key)
        diff = False
        old_data = target_entry.get_values()
        for index in range(len(data_out)):
            if data_out[index] != old_data[index]:
                diff = True
                break
        if not diff and self.should_print_to_output.isChecked() == target_entry.get_print_to_output():
            return

        # Add the entry with a parent set to the 'latest' at current head
        entry = Entry(
            self.currently_selected.get_category(),
            data_out,
            parent_key=target_key,
            print_to_output=self.should_print_to_output.isChecked(),
            character=self.currently_selected.character,
            print_to_history=self.should_print_to_history.isChecked())
        self.engine.add_entry(entry)

        # Allow the user to update any entries that follow afterwards so that inserted updates can propagate their changes
        entry_target = self.engine.get_history_index()
        just_added_key = self.engine.get_entry_key_by_index(entry_target)
        handle_update_later_entries(self.engine, just_added_key)
        self.parent.handle_update(currently_selected=entry_target)

    def handle_update(self, currently_selected, current_history_index):
        if currently_selected is None or currently_selected == -1:
            return
        self.currently_selected = self.engine.get_entry_by_index(currently_selected)

        # Remove all rows
        self.data.clear()
        for row in range(self.form_layout.rowCount()):
            self.form_layout.removeRow(0)

        # Get our category data
        category = self.engine.get_category(self.currently_selected.get_category())
        self.form_layout.addRow("Category:", QLabel(category.get_name()))

        # Parent data
        parent_key = self.currently_selected.get_parent_key()
        parent_entry = None
        parent_values = None
        if parent_key is not None and parent_key != "":
            parent_entry = self.engine.get_entry(parent_key)
            parent_values = parent_entry.get_values()

        # Add in our form information
        data_values = self.currently_selected.get_values()
        props = category.get_properties()
        for row_index in range(len(props)):
            prop = props[row_index]
            name = prop.get_property_name()
            requires_large_input = prop.requires_large_input()
            if name != "":
                # I don't believe this is required any more? TODO: Re-evaluate
                try:
                    value = data_values[row_index]
                except:
                    data_values.append("")
                    value = ""

                if requires_large_input:
                    item = SpellTextEdit(value)
                else:
                    item = QLineEdit(value)

                self.data.append(item)
                to_display = item

                # Handle optional parent
                if parent_values is not None:
                    to_display = QHBoxLayout()
                    if requires_large_input:
                        parent_item = SpellTextEdit(parent_values[row_index])
                    else:
                        parent_item = QLineEdit(parent_values[row_index])
                    parent_item.setEnabled(False)
                    to_display.addWidget(parent_item, stretch=1)
                    to_display.addWidget(item, stretch=1)

                self.form_layout.addRow(name, to_display)
            else:
                self.data.append(None)

        # Print to output
        self.should_print_to_output = QCheckBox()
        self.should_print_to_output.setChecked(self.currently_selected.get_print_to_output())
        self.should_print_to_history = QCheckBox()
        self.should_print_to_history.setChecked(self.currently_selected.print_to_history)
        if parent_entry is not None:
            should_print_to_output_old = QCheckBox()
            should_print_to_output_old.setChecked(parent_entry.get_print_to_output())
            should_print_to_output_old.setEnabled(False)

            should_print_to_output_row = QHBoxLayout()
            should_print_to_output_row.addWidget(should_print_to_output_old, stretch=1)
            should_print_to_output_row.addWidget(self.should_print_to_output, stretch=1)

            self.form_layout.addRow("Print to output?", should_print_to_output_row)

            should_print_to_history_old = QCheckBox()
            should_print_to_history_old.setChecked(parent_entry.print_to_history)
            should_print_to_history_old.setEnabled(False)

            should_print_to_history_row = QHBoxLayout()
            should_print_to_history_row.addWidget(should_print_to_history_old, stretch=1)
            should_print_to_history_row.addWidget(self.should_print_to_history, stretch=1)

            self.form_layout.addRow("Print to history?", should_print_to_history_row)
        else:
            self.form_layout.addRow("Print to output?", self.should_print_to_output)
            self.form_layout.addRow("Print to history?", self.should_print_to_history)

        # Accept button
        self.done_button = QPushButton("Submit Edit")
        self.done_button.clicked.connect(self.handle_submit_button)
        self.form_layout.addRow("", self.done_button)
        if category.can_change_over_time:
            self.new_entry_button = QPushButton("Submit Update")
            self.new_entry_button.clicked.connect(self.handle_update_button)
            self.form_layout.addRow("", self.new_entry_button)


class CategoryView(QWidget):
    def __init__(self, engine: 'LitRPGTools', root_gui, parent, category):
        super().__init__()
        self.engine = engine
        self.root_gui = root_gui
        self.parent = parent
        self.category_name = category
        self.current_layout = list()

        # main layout
        self.main_layout = QVBoxLayout()

        # Main pane
        widget = QWidget()
        widget.setLayout(self.main_layout)
        widget.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")

        # Add scroll
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)

        # Vertical layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(scroll)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def handle_edit_button(self, entry_key_to_edit):
        current_selection = self.root_gui.history_list.currentRow()
        outcome = create_edit_dialog(self.engine, entry_key_to_edit)
        if not outcome:
            return

        # Allow the user to update any entries that follow afterwards so that inserted updates can propagate their changes
        handle_update_later_entries(self.engine, entry_key_to_edit)
        self.root_gui.handle_update(currently_selected=current_selection)

    def handle_update_button(self, entry_key_to_update):
        outcome = create_update_dialog(self.engine, entry_key_to_update)
        if not outcome:
            return

        # Allow the user to update any entries that follow afterwards so that inserted updates can propagate their changes
        entry_target = self.engine.get_history_index()
        just_added_key = self.engine.get_entry_key_by_index(entry_target)
        handle_update_later_entries(self.engine, just_added_key)
        self.root_gui.handle_update(currently_selected=entry_target)

    def handle_update(self, currently_selected, current_history_index):
        # Remove old items
        for item in self.current_layout:
            try:
                self.layout.removeWidget(item)
                item.deleteLater()
            except RuntimeError:
                print("WYY")
        self.current_layout.clear()

        category_items = self.engine.get_category_state_for_entity_at_time(self.category_name, self.parent.character, current_history_index)
        if category_items is None:
            return

        # Category data
        category = self.engine.get_category(self.category_name)
        properties = category.get_properties()

        # Create new items
        for entry_key in category_items:
            form_layout = QFormLayout()
            entry = self.engine.get_entry(entry_key)

            # Skip hidden entries
            if not entry.get_print_to_output() and not self.root_gui.display_hidden.isChecked():
                continue

            # Add in the data
            values = entry.get_values()
            for row_index in range(len(properties)):
                try:
                    value = values[row_index]
                except:
                    values.append("")
                    value = values[row_index]
                if value != "":
                    label = QLabel(value)
                    label.setWordWrap(True)
                    form_layout.addRow(properties[row_index].get_property_name(), label)

            # Add is printed indicator
            is_printed = QCheckBox()
            is_printed.setChecked(entry.get_print_to_output())
            is_printed.setEnabled(False)
            form_layout.addRow("Is printed to output?", is_printed)

            # Add an update button
            edit_button = QPushButton("Edit existing entry.")
            edit_button.clicked.connect(partial(self.handle_edit_button, entry.get_unique_key()))
            update_button = QPushButton("Create update entry at Head.")
            update_button.clicked.connect(partial(self.handle_update_button, entry.get_unique_key()))
            form_layout.addRow("", edit_button)
            if category.can_change_over_time:
                form_layout.addRow("", update_button)

            widget = QWidget()
            widget.setLayout(form_layout)
            widget.setObjectName("bordered")
            self.main_layout.addWidget(widget)
            self.current_layout.append(widget)


class CharacterView(QTabWidget):
    def __init__(self, engine: 'LitRPGTools', root_gui, character):
        super(CharacterView, self).__init__()
        self.engine = engine
        self.root_gui = root_gui
        self.character = character

        # Caches
        self.current_category = 0

        # Content
        self.category_tab_view = QTabWidget()
        self.category_tab_view.currentChanged.connect(self.tab_changed)
        self.category_tab_view.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_tab_view.tabBar().customContextMenuRequested.connect(self.tab_context_menu)

        # Layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.category_tab_view)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setStretch(0, 1000000)
        self.setLayout(self.layout)

    def tab_changed(self, index):
        self.current_category = index
        self.root_gui.handle_update()

    def tab_context_menu(self, position):
        tab_index = self.category_tab_view.tabBar().tabAt(position)
        menu = QMenu()
        move_tab_left_action = QAction("Move Tab Left")
        move_tab_left_action.triggered.connect(partial(self.move_tab_left, tab_index))
        move_tab_right_action = QAction("Move Tab Right")
        move_tab_right_action.triggered.connect(partial(self.move_tab_right, tab_index))
        menu.addActions([move_tab_left_action, move_tab_right_action])
        menu.exec(self.category_tab_view.tabBar().mapToGlobal(position))

    def move_tab_left(self, tab_index):
        self.tab_move(tab_index, tab_index - 1)

    def move_tab_right(self, tab_index):
        if tab_index == len(self.engine.get_categories()):
            return

        self.tab_move(tab_index, tab_index + 1)

    def tab_move(self, start, end):
        categories = self.engine.get_categories()

        # Flip our ordering so our loop works
        if start > end:
            tmp = end
            end = start
            start = tmp

        # Assuming we only move 1 spot each time...
        if end - start != 1:
            raise RuntimeError("Bad Assumption")

        new_categories = OrderedDict()
        count = 0
        key_hold = None
        value_hold = None
        for key, value in categories.items():

            # Store these values and skip without incrementing count
            if count == start:
                key_hold = key
                value_hold = value
            elif count == start + 1:
                new_categories[key] = value
                new_categories[key_hold] = value_hold
            else:
                new_categories[key] = value

            count += 1

        self.engine.set_categories(new_categories)
        self.category_tab_view.tabBar().moveTab(start, end)

    def handle_update(self, currently_selected, current_history_index):
        # Update our existing tab
        current_tab = self.category_tab_view.currentWidget()
        if current_tab is not None:
            current_tab.handle_update(currently_selected, current_history_index)

        # Update our tab bar
        # categories = self.engine.get_categories()
        categories = self.engine.get_character_categories(self.character)
        num_categories = len(categories)
        count = 0
        for category in categories:
            current_name = self.category_tab_view.tabText(count)
            if category != current_name:
                self.category_tab_view.insertTab(count, CategoryView(self.engine, self.root_gui, self, category), category)
            count += 1

        # Remove extra tabs - anything shifted to the right of our expected maximum are no longer needed
        for i in range(self.category_tab_view.count(), num_categories, -1):
            tab_to_delete = self.category_tab_view.widget(i - 1)
            self.category_tab_view.blockSignals(True)
            self.category_tab_view.removeTab(i - 1)
            if tab_to_delete is not None:
                tab_to_delete.deleteLater()
            self.category_tab_view.blockSignals(False)


class MainGUI(QMainWindow):
    def __init__(self, main: 'LitRPGTools', app):
        super().__init__()
        self.engine = main
        self.app = app

        # Theme
        # Force the style to be the same on all OSs:
        self.app.setStyle("Fusion")

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
        self.app.setPalette(palette)

        # General
        self.setMinimumSize(800, 600)
        self.showMaximized()
        self.setWindowTitle("LitRPGTools")

        # Menu Bar
        self.menu_bar = self.menuBar()

        # Main menus
        self.main_menu = self.menu_bar.addMenu("&Main")
        self.save_menu_action = self.main_menu.addAction("Save")
        self.save_menu_action.triggered.connect(self.engine.save)
        self.save_menu_action.setShortcut("Ctrl+s")
        self.save_as_action = self.main_menu.addAction("Save As")
        self.save_as_action.triggered.connect(self.engine.save_as)
        self.load_menu_action = self.main_menu.addAction("Load")
        self.load_menu_action.triggered.connect(self.engine.load)
        self.load_menu_action.setShortcut("Ctrl+o")
        self.load_gsheet_credentials_action = self.main_menu.addAction("Load GSheet Credentials")
        self.load_gsheet_credentials_action.triggered.connect(self.engine.load_gsheets_credentials)
        self.dump_menu_action = self.main_menu.addAction("Dump")
        self.dump_menu_action.triggered.connect(self.engine.dump)

        # Characters Menu
        # self.characters_menu = self.menu_bar.addMenu("&Characters")
        # self.add_character_action = self.characters_menu.addAction("Add Character")
        # self.add_character_action.triggered.connect(self.add_character)
        # self.delete_character_menu = self.characters_menu.addMenu("Delete Character")

        # Categories Menu
        self.categories_menu = self.menu_bar.addMenu("&Categories")
        self.add_category_action = self.categories_menu.addAction("Add Category")
        self.add_category_action.triggered.connect(self.add_category)
        self.edit_category_menu = self.categories_menu.addMenu("Edit Category")
        self.delete_category_menu = self.categories_menu.addMenu("Delete Category")

        # View menu
        self.view_menu = self.menu_bar.addMenu("&View")
        self.display_hidden = QAction("View Hidden")
        self.display_hidden.setCheckable(True)
        self.display_hidden.setChecked(True)
        self.display_hidden.triggered.connect(self.toggle_display_hidden)
        self.display_hidden_menu = self.view_menu.addAction(self.display_hidden)

        # History Sidebar
        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        self.history_list.itemSelectionChanged.connect(self.selection_changed)
        self.create_character_button = QPushButton("Create Character")
        self.create_character_button.clicked.connect(self.create_character)
        self.edit_character_category_button = QPushButton("Edit Character Categories")
        self.edit_character_category_button.clicked.connect(self.edit_character_categories)
        self.create_entry_button = QPushButton("Create Entry Below Highlighted")
        self.create_entry_button.clicked.connect(self.create_entry)
        self.sidebar_layout = QVBoxLayout()
        self.sidebar_layout.addWidget(self.history_list)
        self.sidebar_layout.addWidget(self.create_character_button)
        self.sidebar_layout.addWidget(self.edit_character_category_button)
        self.sidebar_layout.addWidget(self.create_entry_button)
        self.sidebar = QWidget()
        self.sidebar.setLayout(self.sidebar_layout)

        # History actions
        self.set_current_in_history_action = QAction("&Set As Current Item in History")
        self.set_current_in_history_action.triggered.connect(self.set_selected_as_current_item)
        self.delete_in_history_action = QAction("&Delete Item in History")
        self.delete_in_history_action.triggered.connect(self.delete_selected)
        self.label_item_in_history_action = QAction("&Label/Unlabel Item in History")
        self.label_item_in_history_action.triggered.connect(self.label_selected)
        self.move_item_up_action = QAction("&Move Selected Up")
        self.move_item_up_action.triggered.connect(self.move_item_up)
        self.move_item_down_action = QAction("&Move Selected Down")
        self.move_item_down_action.triggered.connect(self.move_item_down)
        self.dulicate_item_no_parents = QAction("&Duplicate (As Independent)")
        self.dulicate_item_no_parents.triggered.connect(self.duplicate_not_child)
        self.dulicate_item_parents = QAction("&Duplicate (As Child)")
        self.dulicate_item_parents.triggered.connect(self.duplicate_to_child)
        self.history_list.addActions([self.set_current_in_history_action, self.delete_in_history_action, self.label_item_in_history_action, self.move_item_up_action, self.move_item_down_action, self.dulicate_item_parents, self.dulicate_item_no_parents])

        # Parent group tab widget
        self.character_tab_view = QTabWidget()
        self.character_tab_view.currentChanged.connect(self.character_tab_changed)
        self.character_tab_view.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.character_tab_view.tabBar().customContextMenuRequested.connect(self.tab_context_menu)

        # Content
        self.selected_tab = SelectedView(self.engine, self)
        self.character_tab_view.blockSignals(True)
        self.character_tab_view.addTab(self.selected_tab, "Currently Selected")
        self.character_tab_view.blockSignals(False)

        # Core Layout
        self.main_pane = VisibleDynamicSplitPanel(Qt.Orientation.Horizontal)
        self.main_pane.addWidget(self.sidebar)
        self.main_pane.addWidget(self.character_tab_view)
        self.main_pane.setStretchFactor(0, 20)
        self.main_pane.setStretchFactor(1, 200)
        self.main_pane.setSizes([200, 1000])
        self.main_pane.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.main_pane)

        # Caches
        self.history_index = -1
        self.current_character = 0
        self.delete_character_actions = dict()
        self.edit_actions = dict()
        self.delete_actions = dict()
        self.selected_parent_index_cache = -1
        self.selected_parent_colour_cache = -1
        self.selected_child_index_cache = -1
        self.selected_child_colour_cache = -1

        # Run an update!
        self.handle_update()
        self.selection_changed()

    def create_character(self):
        dialog = CharacterDialog(self.engine)
        dialog.exec()
        if dialog.viable:
            character = dialog.character_name.text()
            if not character[:1].isalpha():
                return

            self.engine.add_character(character)

            # Update our GUI
            self.handle_update()

    def delete_character(self, character):
        self.engine.delete_character(character)

        # Update our GUI
        self.handle_update()

    def add_category(self):
        category_dialog = CategoryDialog()
        category_dialog.exec()
        if category_dialog.viable:
            category = category_dialog.get_data()
            if not category:
                return
            self.engine.add_category(category)

            # Update our GUI
            self.handle_update()

    def edit_category(self, category_name):
        category = self.engine.get_category(category_name)
        if category is None:
            return

        category_dialog = EditCategoryDialog(category)
        category_dialog.exec()
        if category_dialog.viable:
            category = category_dialog.get_data()
            if not category:
                return

            # Handle plugins update
            self.engine.edit_category(category_name, category)

            # Work through our instructions to edit all category entries
            instructions = category_dialog.get_instructions()
            entries = self.engine.get_all_category_entries(category_name)
            for entry in entries:
                values = entry.get_values()

                # Handle all available instructions in order (ORDER MATTERS)
                for instruction, location in instructions:
                    if instruction == "INSERT_AT":
                        values.insert(location, "")
                    elif instruction == "DELETE":
                        values.pop(location)
                    elif instruction == "MOVE UP":
                        item = values.pop(location)
                        values.insert(location - 1, item)
                    elif instruction == "MOVE DOWN":
                        item = values.pop(location)
                        values.insert(location + 1, item)

            # Update our GUI
            self.handle_update()

    def delete_category(self, category_name):
        self.engine.delete_category(category_name)

        # Update our GUI
        self.handle_update()

    def edit_character_categories(self):
        category_assignment_dialog = CategoryAssignmentDialog(self.engine)
        category_assignment_dialog.exec()
        if category_assignment_dialog.viable:
            character_data = category_assignment_dialog.get_character()
            category_data = category_assignment_dialog.get_data()
            if not character_data or not category_data:
                return
            self.engine.assign_categories_to_character(character_data, category_data)

            # Update our GUI
            self.handle_update()

    def toggle_display_hidden(self):
        self.handle_update()

    def set_selected_as_current_item(self):
        self.engine.set_current_history_index(self.history_list.currentRow())
        self.handle_update()

    def delete_selected(self):
        to_delete = self.history_list.currentRow()
        self.engine.delete_entry_at_index(to_delete)
        self.handle_update(currently_selected=to_delete - 1)

    def label_selected(self):
        selected_entry = self.engine.get_entry_by_index(self.history_list.currentRow())
        entry_key = selected_entry.get_unique_key()
        current_tag = self.engine.get_tag(entry_key)
        if current_tag is None:
            dialog = TagDialog(self.engine)
            dialog.exec()
            if dialog.viable:
                self.engine.add_tag(entry_key, dialog.tag_name.text(), dialog.tag_target.currentText())
                self.handle_update()
        else:
            self.engine.delete_tag(entry_key)
            self.handle_update()

    def move_item_up(self):
        selected_index = self.history_list.currentRow()
        self.engine.move_entry_in_history(selected_index, True)
        self.handle_update(currently_selected=selected_index - 1)

    def move_item_down(self):
        selected_index = self.history_list.currentRow()
        self.engine.move_entry_in_history(selected_index, False)
        self.handle_update(currently_selected=selected_index + 1)

    def duplicate_not_child(self):
        selected_index = self.history_list.currentRow()
        selected_entry = self.engine.get_entry_by_index(selected_index)
        target_dialog = CharacterSelectDialog(self.engine)
        target_dialog.exec()
        if target_dialog.viable:
            entry = Entry(
                selected_entry.get_category(),
                selected_entry.get_values(),
                print_to_output=selected_entry.get_print_to_output(),
                character=target_dialog.character_selector.currentIndex(),
                print_to_history=selected_entry.print_to_history)

            self.engine.add_entry(entry)
            self.handle_update()

    def duplicate_to_child(self):
        selected_index = self.history_list.currentRow()
        selected_entry = self.engine.get_entry_by_index(selected_index)
        parent_key = self.engine.get_most_recent_revision_for_root_entry_key(selected_entry)
        target_dialog = CharacterSelectDialog(self.engine)
        target_dialog.exec()
        if target_dialog.viable:
            entry = Entry(
                selected_entry.get_category(),
                selected_entry.get_values(),
                parent_key=parent_key,
                print_to_output=selected_entry.get_print_to_output(),
                character=target_dialog.character_selector.currentIndex(),
                print_to_history=selected_entry.print_to_history)

            self.engine.add_entry(entry)
            self.history_list.setCurrentRow(self.engine.get_history_index())
            self.handle_update()

    def create_entry(self):
        entry_dialog = CreateEntryDialog(self.engine)
        entry_dialog.exec()
        if entry_dialog.viable:
            entry = Entry(
                entry_dialog.current_category.get_name(),
                entry_dialog.get_data(),
                print_to_output=entry_dialog.print_to_output.isChecked(),
                character=entry_dialog.character_selector.currentIndex(),
                print_to_history=entry_dialog.print_to_history.isChecked())

            self.engine.add_entry(entry)
            self.history_list.setCurrentRow(self.engine.get_history_index())
            self.handle_update()

    def tab_context_menu(self, position):
        tab_index = self.character_tab_view.tabBar().tabAt(position)
        menu = QMenu()
        move_tab_left_action = QAction("Move Tab Left")
        move_tab_left_action.triggered.connect(partial(self.move_tab_left, tab_index))
        move_tab_right_action = QAction("Move Tab Right")
        move_tab_right_action.triggered.connect(partial(self.move_tab_right, tab_index))
        menu.addActions([move_tab_left_action, move_tab_right_action])
        menu.exec(self.character_tab_view.tabBar().mapToGlobal(position))

    def move_tab_left(self, tab_index):
        if tab_index <= 1:
            return

        self.tab_move(tab_index, tab_index - 1)

    def move_tab_right(self, tab_index):
        if tab_index == 0:
            return

        if tab_index == len(self.engine.get_categories()):
            return

        self.tab_move(tab_index, tab_index + 1)

    def tab_move(self, start, end):
        characters = self.engine.get_characters()
        characters.insert(end, characters.pop(start))
        self.character_tab_view.tabBar().moveTab(start, end)

    def selection_changed(self):
        row = self.history_list.currentRow()
        if row != -1:

            # Set default colours
            tags = self.engine.get_tags()
            for i in range(self.history_list.count()):
                entry = self.engine.get_entry_key_by_index(i)
                if entry in tags:
                    self.history_list.item(i).setForeground(Qt.GlobalColor.green)

                elif i == self.engine.get_history_index():
                    self.history_list.item(i).setForeground(Qt.GlobalColor.blue)

                else:
                    self.history_list.item(i).setForeground(Qt.GlobalColor.white)

            # Bail if our currently selected is empty
            currently_selected = self.engine.get_entry_by_index(row)
            if currently_selected is None:
                return

            # Handle child & parent highlighting
            parent_entry = self.engine.get_entry_parent_key(currently_selected.unique_key)
            if parent_entry is not None:
                self.selected_parent_index_cache = self.engine.get_history_index_from_entry(parent_entry)
                item = self.history_list.item(self.selected_parent_index_cache)
                self.selected_parent_colour_cache = item.foreground()
                item.setForeground(Qt.GlobalColor.yellow)
            child_entry = self.engine.get_child_key_from_parent_key(currently_selected.unique_key)
            if child_entry is not None:
                self.selected_child_index_cache = self.engine.get_history_index_from_entry(child_entry)
                item = self.history_list.item(self.selected_child_index_cache)
                self.selected_child_colour_cache = item.foreground()
                item.setForeground(Qt.GlobalColor.yellow)

            # Update our selection panel
            self.selected_tab.handle_update(row, None)

    def character_tab_changed(self, index):
        self.current_character = index
        self.handle_update()

    def handle_update(self, currently_selected=None):
        if currently_selected is None:
            currently_selected = self.history_list.currentRow()

        history_index = self.engine.get_history_index()
        if currently_selected == -1 and history_index != -1:
            currently_selected = history_index

        self.handle_update_menus(currently_selected, history_index)
        self.handle_update_history_list(currently_selected, history_index)
        self.handle_update_current_view(currently_selected,history_index)

    def handle_update_menus(self, currently_selected, current_history_index):
        characters = self.engine.get_characters()
        # self.delete_character_menu.clear()
        # self.delete_character_actions.clear()
        # for character in characters.keys():
        #     action = self.delete_character_menu.addAction(character)
        #     action.triggered.connect(partial(self.delete_character, character))
        #     self.delete_character_actions[character] = action

        categories = self.engine.get_categories()
        self.edit_category_menu.clear()
        self.edit_actions.clear()
        self.delete_category_menu.clear()
        self.delete_actions.clear()
        for category in categories:
            action = self.edit_category_menu.addAction(category)
            action.triggered.connect(partial(self.edit_category, category))
            self.edit_actions[category] = action
            action = self.delete_category_menu.addAction(category)
            action.triggered.connect(partial(self.delete_category, category))
            self.delete_actions[category] = action

    def handle_update_history_list(self, currently_selected, current_history_index):
        # Handle entries TODO: Tags
        self.history_list.blockSignals(True)
        self.history_list.clear()
        history = self.engine.get_history()
        for index in range(len(history)):
            unique_key = history[index]
            entry = self.engine.get_entry(unique_key)
            category = self.engine.get_category(entry.get_category())

            # Choose correct display string template
            parent = self.engine.get_entry_parent_key(unique_key)
            if parent is None:
                category_display = category.get_new_history_entry()
            else:
                category_display = category.get_update_history_entry()

            # Odd formatting
            values = entry.get_values()
            try:
                output = "[" + str(index) + "] (" + str(entry.character) + "): " + category_display.format(*values)
            except:
                output = "[" + str(index) + "] (" + str(entry.character) + "): Bad Category Format"

            # Handle tags:
            tag = self.engine.get_tag(unique_key)
            if tag is not None:
                output += " [TAG: " + tag.get_name() + "]"

            self.history_list.addItem(output)
        self.history_list.blockSignals(False)

        # Set our current point in history
        index = self.engine.get_history_index()
        if currently_selected is None:
            currently_selected = index
        if currently_selected != -1:
            self.history_list.setCurrentRow(currently_selected)

        # Update main display tab
        self.selection_changed()

    def handle_update_current_view(self, currently_selected, current_history_index):
        # Update our existing tab
        # TODO: This may mean that the tab is deleted by the below operations?? Race condition??
        current_tab = self.character_tab_view.currentWidget()
        if current_tab is not None:
            current_tab.handle_update(currently_selected, current_history_index)

        # Update our tab bar
        characters = self.engine.get_characters()
        num_characters = len(characters)

        # Add if missing
        for i in range(num_characters):
            character = characters.keys()[i]
            current_name = self.character_tab_view.tabText(i + 1)
            if character != current_name:
                self.character_tab_view.insertTab(i + 1, CharacterView(self.engine, self, character), character)

        # Delete extraneous tabs, any wrong ones would have been shifted outside the desired range
        for i in range(self.character_tab_view.count() - 1, num_characters, -1):
            tab_to_delete = self.character_tab_view.widget(i - 1)
            self.character_tab_view.blockSignals(True)
            self.character_tab_view.removeTab(i - 1)
            if tab_to_delete is not None:
                tab_to_delete.deleteLater()
            self.character_tab_view.blockSignals(False)
