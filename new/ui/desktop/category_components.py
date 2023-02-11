from functools import partial
from typing import TYPE_CHECKING, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QPushButton, QFormLayout, QLabel, QMessageBox, QMenu, QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem, QListWidget, QAbstractItemView, QScrollArea, QInputDialog
from indexed import IndexedOrderedDict

from new.data import Category, Entry, Character
from new.ui.desktop import dynamic_data_components, entry_components
from new.ui.desktop.custom_generic_components import add_checkbox_in_table_at, VisibleDynamicSplitPanel

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI
    from new.ui.desktop.character_components import CharacterTab


class CategoryTab(QWidget):
    def __init__(self, parent: 'CharacterTab', engine: 'LitRPGToolsEngine', category_id: str):
        super().__init__()
        self._parent = parent
        self._engine = engine
        self.__category_id = category_id

        # Main components
        self._sidebar_widget = CategorySidebar(self, engine)
        self._view_widget = CategoryView(self, engine)

        # Core display set up
        self.__display = VisibleDynamicSplitPanel()
        self.__display.addWidget(self._sidebar_widget)
        self.__display.addWidget(self._view_widget)
        self.__display.setStretchFactor(0, 20)
        self.__display.setStretchFactor(1, 200)
        self.__display.setSizes([200, 1000])

        # Core layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__display)
        self.__layout.setStretchFactor(self.__display, 100)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def draw(self):
        self._sidebar_widget.draw()
        self._view_widget.draw()

    def get_character_id(self):
        return self._parent.character_id

    def get_category_id(self):
        return self.__category_id

    def get_currently_selected(self) -> QListWidgetItem | None:
        return self._sidebar_widget.get_currently_selected()

    def set_curently_selected(self, index: int):
        self._sidebar_widget.set_currently_selected(index)

    def get_should_display_hidden(self):
        return self._sidebar_widget.get_should_display_hidden()

    def get_should_display_dynamic_absolute(self):
        return self._sidebar_widget.view_dynamic_absolute

    def get_should_display_dynamic_relative(self):
        return self._sidebar_widget.view_dynamic_relative

    def _selection_changed(self):
        self._view_widget.draw()


class CategorySidebar(QWidget):
    def __init__(self, parent: CategoryTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # Hidden data buttons
        self.__display_hidden_checkbox = QCheckBox("Display Hidden Entries")
        self.__display_hidden_checkbox.clicked.connect(self.__handle_display_hidden_callback)
        self.__view_hidden = self.__display_hidden_checkbox.isChecked()

        # Dynamic data button
        self.__view_dynamic_data_relative_checkbox = QCheckBox("View Dynamic Data (Respect Current History Index)")
        self.__view_dynamic_data_relative_checkbox.clicked.connect(self.__handle_view_dynamic_data_relative_callback)
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        self.__view_dynamic_data_absolute_checkbox = QCheckBox("View Dynamic Data (Respect Entry Index)")
        self.__view_dynamic_data_absolute_checkbox.clicked.connect(self.__handle_view_dynamic_data_absolute_callback)
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__active_list)
        self.__layout.addWidget(self.__display_hidden_checkbox)
        self.__layout.addWidget(self.__view_dynamic_data_relative_checkbox)
        self.__layout.addWidget(self.__view_dynamic_data_absolute_checkbox)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def __handle_sidebar_selection_changed_callback(self):
        # TODO I keep seeing 'unselections' pop up (meaning a lot of things become None that shouldn't). Perhaps keep some memory here?

        self.__paint_list()
        self._parent._selection_changed()

    def __paint_list(self):
        for i in range(self.__active_list.count()):
            colour = self.__get_list_row_colour_from_context(i)
            self.__active_list.item(i).setForeground(colour)

    def __get_list_row_colour_from_context(self, index) -> Qt.GlobalColor:
        # First check if it's our active 'head'
        if self._engine.get_current_history_index() == index:
            return Qt.GlobalColor.blue

        # Check for a familial relationship with the currently selected
        item = self.__active_list.currentItem()
        if item is None:
            return Qt.GlobalColor.darkMagenta
        entry_id = item.data(Qt.ItemDataRole.UserRole)

        familial_relatives = self._engine.get_entry_revisions_for_id(entry_id)
        if self.__active_list.item(index).data(Qt.ItemDataRole.UserRole) in familial_relatives:
            return Qt.GlobalColor.yellow

        return Qt.GlobalColor.white

    def __handle_display_hidden_callback(self):
        self.__view_hidden = not self.__display_hidden_checkbox.isChecked()
        self._parent._selection_changed()

    def __handle_view_dynamic_data_relative_callback(self):
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        if self.view_dynamic_relative and self.view_dynamic_absolute:
            self.__view_dynamic_data_absolute_checkbox.blockSignals(True)
            self.view_dynamic_absolute = not self.view_dynamic_relative
            self.__view_dynamic_data_absolute_checkbox.setChecked(self.view_dynamic_absolute)
            self.__view_dynamic_data_absolute_checkbox.blockSignals(False)
        self._parent._selection_changed()

    def __handle_view_dynamic_data_absolute_callback(self):
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()
        if self.view_dynamic_absolute and self.view_dynamic_relative:
            self.__view_dynamic_data_relative_checkbox.blockSignals(True)
            self.view_dynamic_relative = not self.view_dynamic_absolute
            self.__view_dynamic_data_relative_checkbox.setChecked(self.view_dynamic_relative)
            self.__view_dynamic_data_relative_checkbox.blockSignals(False)
        self._parent._selection_changed()

    def draw(self):
        self.__fill_active_list()

    def __fill_active_list(self):
        # Get the current selection
        current_selection = self.__active_list.currentRow()

        # Pre-fetch
        character = self._engine.get_character_by_id(self._parent.get_character_id())
        category = self._engine.get_category_by_id(self._parent.get_category_id())
        entries = self._engine.get_entries_for_character_and_category_at_current_history_index(character.unique_id, category.unique_id)

        # Switch what information we populate our list with depending on the view selector
        self.__fill_list(character, category, entries)

        # Handle the unique case where we added our first entry
        if current_selection == -1 and self._engine.get_length_of_history() > 0:
            current_selection = 0

        # Force an update so our text colour can be rendered
        self.__active_list.setCurrentRow(current_selection)

    def __fill_list(self, character: Character, category: Category, entries: List[str]):
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        for entry_id in entries:
            entry = self._engine.get_entry_by_id(entry_id)
            history_index = self._engine.get_entry_index_in_history(entry_id)

            # Skip if hidden and we aren't displaying hidden
            if entry.is_disabled and not self.__view_hidden:
                continue

            # Display string format
            if entry.parent_id is None:
                display_string = category.creation_text
            else:
                display_string = category.update_text
            display_string = self.__fill_display_string(display_string, history_index, character, category, entry)

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


class CategoryView(QScrollArea):
    def __init__(self, parent: CategoryTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Current index box
        self.__current_info = QWidget()
        self.__current_info_layout = QFormLayout()
        self.__current_info.setLayout(self.__current_info_layout)
        self.__current_info_layout.addRow("Current Index in History:", QLabel(str(self._engine.get_current_history_index())))

        # Results
        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.addWidget(self.__current_info)
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view_layout.setStretch(0, 1)
        self.__results_view.setLayout(self.__results_view_layout)
        self.setWidget(self.__results_view)
        self.setWidgetResizable(True)

    def draw(self):
        # Clear out our current data
        for i in reversed(range(1, self.__results_view_layout.count())):
            item = self.__results_view_layout.takeAt(i)
            if item is not None:
                try:
                    item.widget().deleteLater()
                except AttributeError as e:
                    continue

        # Retrieve our selection
        item = self._parent.get_currently_selected()
        if item is None:
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        entry = self._engine.get_entry_by_id(entry_id)
        self.__draw_entry(entry)

    def __draw_entry(self, entry: Entry):
        character = self._engine.get_character_by_id(entry.character_id)
        category = self._engine.get_category_by_id(entry.category_id)

        # Switch which dynamic data we display depending on what button is ticked
        current_index = self._engine.get_entry_index_in_history(entry.unique_id)
        target_index = None
        should_display_dynamic_data = False
        if self._parent.get_should_display_dynamic_absolute():
            should_display_dynamic_data = True
        elif self._parent.get_should_display_dynamic_relative():
            target_index = self._engine.get_current_history_index()
            should_display_dynamic_data = True

        # Form
        entry_form = QWidget()
        entry_form_layout = QFormLayout()
        entry_components.create_entry_form(self._engine, entry_form_layout, character, category, entry, current_index, header=True, readonly=True, translate_with_dynamic_data=should_display_dynamic_data, dynamic_data_index=target_index)
        entry_form.setLayout(entry_form_layout)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        set_as_head_button = QPushButton("Set as Current Entry in History")
        set_as_head_button.clicked.connect(partial(self.__handle_set_as_head_callback, entry))
        entry_controls_layout.addWidget(set_as_head_button)
        entry_edit_button = QPushButton("Edit")
        entry_edit_button.clicked.connect(partial(self.__handle_edit_callback, entry))
        entry_controls_layout.addWidget(entry_edit_button)
        entry_update_button = QPushButton("Update")
        entry_update_button.clicked.connect(partial(self.__handle_update_callback, entry))
        entry_controls_layout.addWidget(entry_update_button)
        entry_series_delete_button = QPushButton("Delete Series")
        entry_series_delete_button.clicked.connect(partial(self.__handle_delete_series_callback, entry))
        entry_controls_layout.addWidget(entry_series_delete_button)
        entry_delete_button = QPushButton("Delete")
        entry_delete_button.clicked.connect(partial(self.__handle_delete_callback, entry))
        entry_controls_layout.addWidget(entry_delete_button)
        entry_duplicate_button = QPushButton("Duplicate")
        entry_duplicate_button.clicked.connect(partial(self.__handle_duplicate_callback, entry))
        entry_controls_layout.addWidget(entry_duplicate_button)
        entry_controls_layout.addStretch()
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
        self.__results_view_layout.addWidget(entry_widget)
        self.__results_view_layout.setStretch(1, 100)

    def __handle_set_as_head_callback(self, entry: Entry):
        entry_components.set_entry_as_head(self._engine, entry)

    def __handle_edit_callback(self, entry: Entry):
        entry_components.edit_entry(self._engine, self, entry)
        self._parent.draw()

    def __handle_update_callback(self, entry: Entry):
        update = entry_components.update_entry(self._engine, self, entry)
        if update is not None:
            self._parent.set_curently_selected(self._engine.get_entry_index_in_history(update.unique_id))
        self._parent.draw()

    def __handle_delete_series_callback(self, entry: Entry):
        entry_components.delete_entry_series(self._engine, self, entry)
        self._parent.set_curently_selected(self._engine.get_current_history_index())
        self._parent.draw()

    def __handle_delete_callback(self, entry: Entry):
        entry_components.delete_entry(self._engine, self, entry)
        self._parent.set_curently_selected(self._engine.get_current_history_index())
        self._parent.draw()

    def __handle_duplicate_callback(self, entry: Entry):
        entry_components.duplicate_entry(self._engine, entry)
        self._parent.set_curently_selected(self._engine.get_current_history_index())
        self._parent.draw()


class CategoryDialog(QDialog):
    def __init__(self, engine, category: Category = None):
        super(CategoryDialog, self).__init__()
        self.__engine = engine
        self.__category = category

        # Outputs
        self.success = False
        self.edit_instructions = list()
        self.generated_category = None

        # General
        self.setWindowTitle("New Category.")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        # Category contents
        self.__category_name = QLineEdit()
        self.__category_properties_table = QTableWidget()
        self.__category_properties_table.setColumnCount(2)
        self.__category_properties_table.setHorizontalHeaderItem(0, QTableWidgetItem("Property Text"))
        self.__category_properties_table.setHorizontalHeaderItem(1, QTableWidgetItem("Requires Large Input Text"))
        self.__category_properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.__category_properties_table.setRowCount(1)
        self.__category_properties_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))

        # History information display in side panel
        self.__created_history_field = QLineEdit()
        self.__updated_history_field = QLineEdit()

        # Behaviour switches
        self.__print_to_overview_button = QCheckBox()
        self.__can_change_over_time = QCheckBox()
        self.__is_singleton = QCheckBox()

        # Dynamic data modifications
        self.__dynamic_data_table = dynamic_data_components.create_dynamic_data_table()
        self.__dynamic_data_table.cellChanged.connect(partial(dynamic_data_components.handle_dynamic_data_table_cell_changed_callback, self.__dynamic_data_table))

        # Dynamic modification templating
        self.__dynamic_data_templates_table = dynamic_data_components.create_dynamic_data_table()
        self.__dynamic_data_templates_table.cellChanged.connect(partial(dynamic_data_components.handle_dynamic_data_table_cell_changed_callback, self.__dynamic_data_templates_table))

        # Buttons
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Form
        self.__layout = QFormLayout()
        self.__layout.addRow("Category Name", self.__category_name)
        self.__layout.addRow("Category Properties", self.__category_properties_table)
        self.__layout.addRow("", QLabel("For the next section, please input your 'display' string for each situation. Use {0} to insert entry data from the 1st row (row headers are correct)."))
        self.__layout.addRow("New Entry History Summary:", self.__created_history_field)
        self.__layout.addRow("Update Entry History Summary:", self.__updated_history_field)
        self.__layout.addRow("Category displayed in Overview?", self.__print_to_overview_button)
        self.__layout.addRow("Can entries change over time?", self.__can_change_over_time)
        self.__layout.addRow("Is Singleton?", self.__is_singleton)
        self.__layout.addRow("", QLabel("The next section deals with dynamic data. Only use if you understand what is going on."))
        self.__layout.addRow("Dynamic Data Modifications", self.__dynamic_data_table)
        self.__layout.addRow("", QLabel("The next section deals with dynamic data modification templates for all entries. Only use if you understand what is going on."))
        self.__layout.addRow("Dynamic Data Modification Templates", self.__dynamic_data_templates_table)
        self.__layout.addRow(self.__cancel_button, self.__done_button)
        self.setLayout(self.__layout)
        self.setMinimumWidth(640)

        # Set the data
        if category is None:
            self.__category_properties_table.setItem(0, 0, QTableWidgetItem(""))
            add_checkbox_in_table_at(self.__category_properties_table, 0)
            self.__category_properties_table.cellChanged.connect(self.__handle_contents_cell_changed_callback)

            # Dynamic data modifications table
            self.__dynamic_data_table.blockSignals(True)
            dynamic_data_components.fill_dynamic_modifications_table(self.__dynamic_data_table, {})
            self.__dynamic_data_table.blockSignals(False)

            # Dynamic data modifications table
            self.__dynamic_data_templates_table.blockSignals(True)
            dynamic_data_components.fill_dynamic_modifications_table(self.__dynamic_data_templates_table, {})
            self.__dynamic_data_templates_table.blockSignals(False)

        else:
            self.__category_name.setText(category.name)

            # Content table
            self.__category_properties_table.blockSignals(True)
            self.__category_properties_table.setRowCount(len(category.contents))
            for i, (k, v) in enumerate(category.contents.items()):
                self.__category_properties_table.setItem(i, 0, QTableWidgetItem(k))
                add_checkbox_in_table_at(self.__category_properties_table, i, state=v)
            self.__category_properties_table.blockSignals(False)

            # History display
            self.__created_history_field.setText(category.creation_text)
            self.__updated_history_field.setText(category.update_text)

            # Behaviour switches
            self.__print_to_overview_button.setChecked(category.print_to_character_overview)
            self.__can_change_over_time.setChecked(category.can_update)
            self.__is_singleton.setChecked(category.single_entry_only)

            # Dynamic data modifications table
            self.__dynamic_data_table.blockSignals(True)
            dynamic_data_components.fill_dynamic_modifications_table(self.__dynamic_data_table, category.dynamic_data_operations)
            self.__dynamic_data_table.blockSignals(False)

            # Dynamic data modifications table
            self.__dynamic_data_templates_table.blockSignals(True)
            dynamic_data_components.fill_dynamic_modifications_table(self.__dynamic_data_templates_table, category.dynamic_data_operation_templates)
            self.__dynamic_data_templates_table.blockSignals(False)

            # Add context menu for editing the order of contents
            self.__category_properties_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self.__category_properties_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.__category_properties_table.customContextMenuRequested.connect(self.__create_content_context_menu)

    def __handle_contents_cell_changed_callback(self, row, column):
        # Only interested in the primary column updates
        if column != 0:
            return

        # Ensure that something was actually added so we aren't adding rows willy-nilly, also that we are editing the last row
        item = self.__category_properties_table.item(row, 0)
        if item is None:
            return
        item = item.text()
        if item == "":
            return
        target_row = row + 1
        if self.__category_properties_table.rowCount() != target_row:
            return

        # Add a row
        self.__category_properties_table.blockSignals(True)
        self.__category_properties_table.insertRow(target_row)
        self.__category_properties_table.setVerticalHeaderItem(target_row, QTableWidgetItem(str(target_row)))
        add_checkbox_in_table_at(self.__category_properties_table, target_row)
        self.__category_properties_table.blockSignals(False)

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        contents = IndexedOrderedDict()
        for row_index in range(self.__category_properties_table.rowCount()):
            item = self.__category_properties_table.item(row_index, 0)

            # Continue if empty
            if item is None:
                continue
            property_name = item.text()
            if property_name == "":
                continue

            # Determine if we should be using a large input format
            contents[property_name] = self.__category_properties_table.cellWidget(row_index, 1).checkState() == Qt.CheckState.Checked

        # Build our dynamic data
        modifications = dynamic_data_components.extract_dynamic_data_table_data(self.__dynamic_data_table)
        if modifications is None:
            self.__handle_cancel_callback()
            return

        # Build our dynamic data templates for entries
        template_modifications = dynamic_data_components.extract_dynamic_data_table_data(self.__dynamic_data_templates_table)
        if modifications is None:
            self.__handle_cancel_callback()
            return

        # Empty == bail
        if len(contents) == 0:
            self.generated_category = None
        else:
            print_to_overview = self.__print_to_overview_button.isChecked()
            can_update = self.__can_change_over_time.isChecked()
            single_entry = self.__is_singleton.isChecked()
            self.generated_category = Category(
                self.__category_name.text(),
                contents,
                creation_text=self.__created_history_field.text(),
                update_text=self.__updated_history_field.text(),
                print_to_character_overview=print_to_overview,
                can_update=can_update,
                single_entry_only=single_entry,
                dynamic_data_operations=modifications,
                dynamic_data_operation_templates=template_modifications
            )

        # Check if an item has been removed from our original input list
        if "DELETE" in self.edit_instructions:
            result = QMessageBox.question(
                self,
                "Are you sure?",
                "You may have removed a category field. This will result in all associated data being deleted. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
            self.success = result == QMessageBox.StandardButton.Yes
        else:
            self.success = True
        self.close()

    def __create_content_context_menu(self, pos):
        if self.__category_properties_table.itemAt(pos) is None:
            return

        row = self.__category_properties_table.itemAt(pos).row()

        # Context menu actions
        rename_action = QAction("Rename", self)
        rename_action.triggered.connect(partial(self.__handle_rename_callback, row))
        insert_above_action = QAction("Insert Row Above", self)
        insert_above_action.triggered.connect(partial(self.__insert_row_above, row))
        insert_row_below_action = QAction("Insert Row Below", self)
        insert_row_below_action.triggered.connect(partial(self.__insert_row_below, row))
        delete_row_action = QAction("Delete Row", self)
        delete_row_action.triggered.connect(partial(self.__delete_row, row))
        move_row_up_action = QAction("Move Row Up", self)
        move_row_up_action.triggered.connect(partial(self.__move_row_up, row))
        move_row_down_action = QAction("Move Row Down", self)
        move_row_down_action.triggered.connect(partial(self.__move_row_down, row))

        # Menu
        menu = QMenu()
        menu.addAction(rename_action)
        menu.addAction(insert_above_action)
        menu.addAction(insert_row_below_action)
        menu.addAction(delete_row_action)
        menu.addAction(move_row_up_action)
        menu.addAction(move_row_down_action)
        menu.exec(self.__category_properties_table.mapToGlobal(pos))

    def __handle_rename_callback(self, row):
        # Current
        current_text = self.__category_properties_table.itemAt(row, 0).text()

        # Create a line edit dialog box to get the new name
        new_name, ok = QInputDialog.getText(self, "New Category Property Name?", "What do you want to replace: " + current_text + " with?")
        if not ok:
            return

        # Change our props
        self.__category_properties_table.setItem(row, 0, QTableWidgetItem(new_name))

    def __insert_row_above(self, row):
        # Create a line edit dialog box to get the new name
        new_name, ok = QInputDialog.getText(self, "New Category Property Name?", "What will be the new property name?")
        if not ok:
            return

        # Add our instruction
        self.edit_instructions.append(("INSERT_AT", row))

        # Perform action @ GUI
        self.__category_properties_table.insertRow(row)
        self.__category_properties_table.setItem(row, 0, QTableWidgetItem(new_name))
        add_checkbox_in_table_at(self.__category_properties_table, row)

    def __insert_row_below(self, row):
        row = row + 1
        self.__insert_row_above(row)

    def __delete_row(self, row):
        # Add our instruction
        self.edit_instructions.append(("DELETE", row))

        # Perform action @ GUI
        self.__category_properties_table.removeRow(row)

    def __move_row_up(self, row):
        # Add our instruction
        self.edit_instructions.append(("MOVE UP", row))

        # Perform action @ GUI
        self.__category_properties_table.insertRow(row - 1)
        for column in range(self.__category_properties_table.columnCount()):
            item = self.__category_properties_table.takeItem(row + 1, column)
            if item:
                self.__category_properties_table.setItem(row - 1, column, item)
        self.__category_properties_table.removeRow(row + 1)

    def __move_row_down(self, row):
        # Add our instruction
        self.edit_instructions.append(("MOVE DOWN", row))

        # Perform action @ GUI
        self.__category_properties_table.insertRow(row + 1)
        for column in range(self.__category_properties_table.columnCount()):
            item = self.__category_properties_table.takeItem(row, column)
            if item:
                self.__category_properties_table.setItem(row + 1, column, item)
        self.__category_properties_table.removeRow(row)


def add_or_edit_category(engine: 'LitRPGToolsEngine', category: Category | None):
    # Build a dialog to edit the current category information
    edit_category_dialog = CategoryDialog(engine, category)
    edit_category_dialog.exec()

    # Validate dialog output
    if not edit_category_dialog.success:
        return

    # Add our new category
    if category is None:
        engine.add_category(edit_category_dialog.generated_category)
        category = edit_category_dialog.generated_category

    # Edit the category in our engine
    else:
        new_category = edit_category_dialog.generated_category
        new_category.unique_id = category.unique_id
        engine.edit_category(new_category, edit_category_dialog.edit_instructions)
        category = new_category

    return category


def delete_category(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', category: Category):
    engine.delete_category(category)
    parent.handle_update()


def create_category_form(target_layout, category: Category):
    # Add our header info
    target_layout.addRow("Category:", QLabel(category.name))
    target_layout.addRow("", QLabel())

    # Add our contents
    target_layout.addRow("Property Text", QLabel("Requires Large Input"))
    for index, (key, large_input) in enumerate(category.contents.items()):
        check_box = QCheckBox()
        check_box.setChecked(large_input)
        check_box.setEnabled(False)
        target_layout.addRow(key, check_box)

    # Update strings
    target_layout.addRow("Creation text:", QLabel(category.creation_text))
    target_layout.addRow("Update text:", QLabel(category.update_text))

    # Add configs
    print_to_overview_check_box = QCheckBox()
    print_to_overview_check_box.setChecked(category.print_to_character_overview)
    print_to_overview_check_box.setEnabled(False)
    target_layout.addRow("Print to Overview Disabled?", print_to_overview_check_box)

    can_update_check_box = QCheckBox()
    can_update_check_box.setChecked(category.can_update)
    can_update_check_box.setEnabled(False)
    target_layout.addRow("Can Update?", can_update_check_box)

    is_singleton_check_box = QCheckBox()
    is_singleton_check_box.setChecked(category.single_entry_only)
    is_singleton_check_box.setEnabled(False)
    target_layout.addRow("Is singleton?", is_singleton_check_box)

    # Dynamic data modifications
    ddm_widget = dynamic_data_components.create_dynamic_data_table(readonly=True)
    dynamic_data_components.fill_dynamic_modifications_table(ddm_widget, category.dynamic_data_operations, readonly=True)
    target_layout.addRow("Dynamic Data", ddm_widget)

    # Dynamic data modification templates
    ddmt_widget = dynamic_data_components.create_dynamic_data_table(readonly=True)
    dynamic_data_components.fill_dynamic_modifications_table(ddmt_widget, category.dynamic_data_operation_templates, readonly=True)
    target_layout.addRow("Dynamic Data Templates for Entries", ddmt_widget)
