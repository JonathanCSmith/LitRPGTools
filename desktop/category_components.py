from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QPushButton, QFormLayout, QLabel, QMessageBox, QMenu, QWidget, QHBoxLayout, QVBoxLayout, QListWidgetItem, QListWidget, QAbstractItemView, QScrollArea, QInputDialog
from indexed import IndexedOrderedDict

from data.models import Category
from desktop import dynamic_data_components, entry_components
from desktop.custom_generic_components import add_checkbox_in_table_at, VisibleDynamicSplitPanel, MemoryModalDialog, Content

if TYPE_CHECKING:
    from desktop.guis import DesktopGUI
    from desktop.character_components import CharacterTab


class CategoryTab(QWidget, Content):
    def __init__(self, root_gui: 'DesktopGUI', character_tab: 'CharacterTab', category_id: str):
        super().__init__()
        self.root_gui = root_gui
        self.character_tab = character_tab
        self.category_id = category_id

        # Main components
        self.__sidebar_widget = QWidget()
        self.__setup_sidebar()

        self.__entry_view = QScrollArea()
        self.__setup_entry_view()

        # Core display set up
        self.__display = VisibleDynamicSplitPanel()
        self.__display.addWidget(self.__sidebar_widget)
        self.__display.addWidget(self.__entry_view)
        self.__display.setStretchFactor(0, 20)
        self.__display.setStretchFactor(1, 200)
        self.__display.setSizes([200, 1000])

        # Core layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__display)
        self.__layout.setStretchFactor(self.__display, 100)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def __setup_sidebar(self):
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
        self.__sidebar_widget.setLayout(self.__layout)

    def __setup_entry_view(self):
        self.selected_entry_id = None

        # Current index box
        self.__current_info = QWidget()
        self.__current_info_layout = QFormLayout()
        self.__current_info.setLayout(self.__current_info_layout)
        self.__current_info_layout.addRow("Current Index in History:", QLabel(str(self.root_gui.runtime.data_manager.get_current_history_index())))

        # Results
        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.addWidget(self.__current_info)
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view_layout.setStretch(0, 1)
        self.__results_view.setLayout(self.__results_view_layout)
        self.__entry_view.setWidget(self.__results_view)
        self.__entry_view.setWidgetResizable(True)

    def fill_content(self):
        self.clear_content()

        self.__fill_active_list()
        self.__fill_entry_view()

    def __fill_active_list(self):
        currently_selected = self.__active_list.currentRow()
        current_history_entry = self.root_gui.runtime.data_manager.get_entry_id_by_history_index(self.root_gui.runtime.data_manager.get_current_history_index())
        current_entry_selected = None
        if currently_selected != -1:
            current_entry_selected = self.__active_list.item(currently_selected).data(Qt.ItemDataRole.UserRole)

        # Pre-fetch
        character = self.root_gui.runtime.data_manager.get_character_by_id(self.character_tab.character_id)
        category = self.root_gui.runtime.data_manager.get_category_by_id(self.category_id)
        entries = self.root_gui.runtime.data_manager.get_entries_for_character_and_category_at_current_history_index(character.unique_id, category.unique_id)

        # Block signals and clear list
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        for entry_id in entries:
            entry = self.root_gui.runtime.data_manager.get_entry_by_id(entry_id)

            # Skip if hidden and we aren't displaying hidden
            if entry.is_disabled and not self.__view_hidden:
                continue

            # Build our item
            display_string = self.root_gui.create_entry_summary_string(entry_id)
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)

            # If the item is the current history head
            if entry_id == current_history_entry:
                colour = Qt.GlobalColor.blue
            elif current_entry_selected in self.root_gui.runtime.data_manager.get_entry_revisions_for_id(entry_id):
                colour = Qt.GlobalColor.yellow
            else:
                colour = Qt.GlobalColor.white
            item.setForeground(colour)

            # Add the string
            self.__active_list.addItem(item)

        # Return signals
        self.__active_list.setCurrentRow(currently_selected)
        self.__active_list.blockSignals(False)

    def __fill_entry_view(self):
        # Clear our current data
        result = self.__results_view_layout.itemAt(1)
        if result is not None:
            result_widget = result.widget()
            result_widget.deleteLater()

        # Obtain the currently selected item and bail if there's nothing
        item = self.__active_list.currentItem()
        if item is None:
            self.selected_entry_id = None
            return

        # Store the current selection
        self.selected_entry_id = item.data(Qt.ItemDataRole.UserRole)
        entry = self.root_gui.runtime.data_manager.get_entry_by_id(self.selected_entry_id)

        # Gather the additional data for this entry
        character = self.root_gui.runtime.data_manager.get_character_by_id(entry.character_id)
        category = self.root_gui.runtime.data_manager.get_category_by_id(entry.category_id)

        # Switch which dynamic data we display depending on what button is ticked
        current_index = self.root_gui.runtime.data_manager.get_entry_index_in_history(self.selected_entry_id)
        target_index = None
        should_display_dynamic_data = False
        if self.view_dynamic_absolute:
            should_display_dynamic_data = True
        elif self.view_dynamic_relative:
            target_index = self.root_gui.runtime.data_manager.get_current_history_index()
            should_display_dynamic_data = True

        # Form
        entry_form = QWidget()
        entry_form_layout = QFormLayout()
        entry_components.create_entry_form(
            self.root_gui,
            entry_form_layout,
            character,
            category,
            entry,
            current_index,
            header=True,
            readonly=True,
            translate_with_dynamic_data=should_display_dynamic_data,
            dynamic_data_index=target_index)
        entry_form.setLayout(entry_form_layout)

        # Context menu
        entry_form.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        entry_form.customContextMenuRequested.connect(self.__handle_context_menu)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        set_as_head_button = QPushButton("Set as Current Entry in History")
        set_as_head_button.clicked.connect(self.__handle_set_as_head_callback)
        entry_controls_layout.addWidget(set_as_head_button)
        entry_edit_button = QPushButton("Edit")
        entry_edit_button.clicked.connect(self.__handle_edit_callback)
        entry_controls_layout.addWidget(entry_edit_button)
        if category.can_update:
            entry_update_button = QPushButton("Update")
            entry_update_button.clicked.connect(self.__handle_update_callback)
            entry_controls_layout.addWidget(entry_update_button)
        entry_force_update_button = QPushButton("Force Update")
        entry_force_update_button.clicked.connect(self.__handle_force_update_callback)
        entry_controls_layout.addWidget(entry_force_update_button)
        entry_series_delete_button = QPushButton("Delete Series")
        entry_series_delete_button.clicked.connect(self.__handle_delete_series_callback)
        entry_controls_layout.addWidget(entry_series_delete_button)
        entry_delete_button = QPushButton("Delete")
        entry_delete_button.clicked.connect(self.__handle_delete_callback)
        entry_controls_layout.addWidget(entry_delete_button)
        entry_duplicate_button = QPushButton("Duplicate")
        entry_duplicate_button.clicked.connect(self.__handle_duplicate_callback)
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
        self.__results_view_layout.insertWidget(1, entry_widget, 1000)

    def clear_content(self):
        self.blockSignals(True)
        self.__active_list.clear()
        self.selected_entry_id = None
        self.__fill_entry_view()  # Should clear based on us having no item selected
        self.blockSignals(False)

    def __handle_sidebar_selection_changed_callback(self):
        self.__repaint_list()
        self.__fill_entry_view()

    def __repaint_list(self):
        self.__active_list.blockSignals(True)
        currently_selected = self.__active_list.currentRow()
        current_history_entry = self.root_gui.runtime.data_manager.get_entry_id_by_history_index(self.root_gui.runtime.data_manager.get_current_history_index())
        current_entry_selected = None
        if currently_selected != -1:
            current_entry_selected = self.__active_list.item(currently_selected).data(Qt.ItemDataRole.UserRole)

        for i in range(self.__active_list.count()):
            entry_id = self.__active_list.item(i).data(Qt.ItemDataRole.UserRole)

            # Get and set the colour
            if entry_id == current_history_entry:
                colour = Qt.GlobalColor.blue
            elif current_entry_selected in self.root_gui.runtime.data_manager.get_entry_revisions_for_id(entry_id):
                colour = Qt.GlobalColor.yellow
            else:
                colour = Qt.GlobalColor.white
            self.__active_list.item(i).setForeground(colour)
        self.__active_list.blockSignals(False)

    def __handle_display_hidden_callback(self):
        self.__view_hidden = self.__display_hidden_checkbox.isChecked()
        self.fill_content()

    def __handle_view_dynamic_data_relative_callback(self):
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        if self.view_dynamic_relative and self.view_dynamic_absolute:
            self.__view_dynamic_data_absolute_checkbox.blockSignals(True)
            self.view_dynamic_absolute = not self.view_dynamic_relative
            self.__view_dynamic_data_absolute_checkbox.setChecked(self.view_dynamic_absolute)
            self.__view_dynamic_data_absolute_checkbox.blockSignals(False)
        self.__fill_entry_view()

    def __handle_view_dynamic_data_absolute_callback(self):
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()
        if self.view_dynamic_absolute and self.view_dynamic_relative:
            self.__view_dynamic_data_relative_checkbox.blockSignals(True)
            self.view_dynamic_relative = not self.view_dynamic_absolute
            self.__view_dynamic_data_relative_checkbox.setChecked(self.view_dynamic_relative)
            self.__view_dynamic_data_relative_checkbox.blockSignals(False)
        self.__fill_entry_view()

    def __handle_context_menu(self, pos):
        if self.selected_entry_id is None:
            return

        context_menu = QMenu(self)

        # Create actions for the context menu
        copy_id_to_clipboard_action = QAction("Copy Current Entry ID", self)
        copy_id_to_clipboard_action.triggered.connect(self.root_gui.copy_id_to_clipboard(self.selected_entry_id))

        # Add actions to the context menu
        context_menu.addAction(copy_id_to_clipboard_action)

        # Show the context menu at the mouse position
        context_menu.exec(self.mapToGlobal(pos))

    def __handle_data_changed(self):
        # Update the GUI
        self.__fill_active_list()

        # Search our history list for the entry, retarget our pointer, repaint accordingly
        self.blockSignals(True)
        target_index = 0
        for i in range(self.__active_list.count()):
            potential_match = self.__active_list.item(i).data(Qt.ItemDataRole.UserRole)
            if potential_match == self.selected_entry_id:
                target_index = i
                break
        self.__active_list.setCurrentRow(target_index)
        self.__repaint_list()
        self.blockSignals(False)

    def __handle_set_as_head_callback(self):
        entry_components.set_entry_as_head(self.root_gui, self.selected_entry_id)
        self.__repaint_list()
        self.__fill_entry_view()

    def __handle_edit_callback(self):
        entry_components.edit_entry(self.root_gui, self, self.selected_entry_id)
        self.__fill_active_list()  # In case our summary data changed
        self.__fill_entry_view()

    def __handle_update_callback(self):
        updated_entry = entry_components.update_entry(self.root_gui, self, self.selected_entry_id)
        if updated_entry is not None:
            self.selected_entry_id = updated_entry.unique_id
            self.__handle_data_changed()
            self.__fill_entry_view()

    def __handle_force_update_callback(self):
        updated_entry = entry_components.force_update_entry_with_no_changes(self.root_gui,self.selected_entry_id)
        if updated_entry is not None:
            self.selected_entry_id = updated_entry.unique_id
            self.__handle_data_changed()
            self.__fill_entry_view()

    def __handle_delete_series_callback(self):
        entry_components.delete_entry_series(self.root_gui, self.selected_entry_id)
        self.selected_entry_id = None
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_delete_callback(self):
        current_row_index = self.__active_list.model().match(0, Qt.ItemDataRole.UserRole, self.selected_entry_id)
        if current_row_index == 0 and self.__active_list.count() > 1:
            target_entry_id = self.__active_list.item(1).data(Qt.ItemDataRole.UserRole)
        elif current_row_index == 0 and self.__active_list.count() == 1:
            target_entry_id = None
        else:
            target_entry_id = self.__active_list.item(current_row_index - 1).data(Qt.ItemDataRole.UserRole)

        entry_components.delete_entry(self.root_gui, self.selected_entry_id)
        self.selected_entry_id = target_entry_id
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_duplicate_callback(self):
        entry = entry_components.duplicate_entry(self.root_gui, self.selected_entry_id)
        self.selected_entry_id = entry.unique_id
        self.__handle_data_changed()
        self.__fill_entry_view()


class CategoryDialog(MemoryModalDialog):
    def __init__(self, gui: 'DesktopGUI', category: Category = None):
        super(CategoryDialog, self).__init__(gui=gui)
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
        self.__dynamic_data_table = dynamic_data_components.create_dynamic_data_table(self.desktop_gui)
        self.__dynamic_data_table.cellChanged.connect(partial(dynamic_data_components.handle_dynamic_data_table_cell_changed_callback, self.__dynamic_data_table))

        # Dynamic modification templating
        self.__dynamic_data_templates_table = dynamic_data_components.create_dynamic_data_table(self.desktop_gui)
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
        self.__layout.addRow("", QLabel("The next section deals with dynamic data specific to the CATEGORY. Only use if you understand what is going on."))
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
            cell_widget = self.__category_properties_table.cellWidget(row_index, 1)
            if cell_widget is not None:
                contents[property_name] = cell_widget.checkState() == Qt.CheckState.Checked

        # Build our dynamic data
        modifications = dynamic_data_components.extract_dynamic_data_table_data(self.__dynamic_data_table)
        if modifications is None:
            self.__handle_cancel_callback()
            return

        # Build our dynamic data templates for entries
        template_modifications = dynamic_data_components.extract_dynamic_data_table_data(self.__dynamic_data_templates_table)
        if template_modifications is None:
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

            # Need to check for cell widgets and handle
            else:
                cell_widget = self.__category_properties_table.cellWidget(row + 1, column)
                if isinstance(cell_widget, QCheckBox):
                    check_box = QCheckBox()
                    check_box.setChecked(cell_widget.isChecked())
                    self.__category_properties_table.setCellWidget(row - 1, column, check_box)

        self.__category_properties_table.removeRow(row + 1)

    def __move_row_down(self, row):
        # Add our instruction
        self.edit_instructions.append(("MOVE DOWN", row))

        # Perform action @ GUI
        self.__category_properties_table.insertRow(row + 2)
        for column in range(self.__category_properties_table.columnCount()):
            item = self.__category_properties_table.takeItem(row, column)
            if item:
                self.__category_properties_table.setItem(row + 2, column, item)

            # Need to check for cell widgets and handle
            else:
                cell_widget = self.__category_properties_table.cellWidget(row, column)
                if isinstance(cell_widget, QCheckBox):
                    check_box = QCheckBox()
                    check_box.setChecked(cell_widget.isChecked())
                    self.__category_properties_table.setCellWidget(row + 2, column, check_box)

        self.__category_properties_table.removeRow(row)


def add_or_edit_category(root_gui: 'DesktopGUI', category_id: str | None):
    category = root_gui.runtime.data_manager.get_category_by_id(category_id)

    # Build a dialog to edit the current category information
    edit_category_dialog = CategoryDialog(root_gui, category)
    edit_category_dialog.exec()

    # Validate dialog output
    if not edit_category_dialog.success:
        return

    # Add our new category
    if category is None:
        root_gui.runtime.data_manager.add_category(edit_category_dialog.generated_category)
        category = edit_category_dialog.generated_category

    # Edit the category in our engine
    else:
        new_category = edit_category_dialog.generated_category
        new_category.unique_id = category.unique_id
        root_gui.runtime.data_manager.edit_category(new_category, edit_category_dialog.edit_instructions)
        category = new_category

    return category


def delete_category(root_gui: 'DesktopGUI', category_id: str):
    root_gui.runtime.data_manager.delete_category(category_id)


def create_category_form(root_gui_object: 'DesktopGUI', target_layout, category: Category):
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
    ddm_widget = dynamic_data_components.create_dynamic_data_table(root_gui_object, readonly=True)
    dynamic_data_components.fill_dynamic_modifications_table(ddm_widget, category.dynamic_data_operations, readonly=True)
    target_layout.addRow("Dynamic Data", ddm_widget)

    # Dynamic data modification templates
    ddmt_widget = dynamic_data_components.create_dynamic_data_table(root_gui_object, readonly=True)
    dynamic_data_components.fill_dynamic_modifications_table(ddmt_widget, category.dynamic_data_operation_templates, readonly=True)
    target_layout.addRow("Dynamic Data Templates for Entries", ddmt_widget)
