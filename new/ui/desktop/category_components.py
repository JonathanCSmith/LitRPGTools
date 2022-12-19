from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QPushButton, QFormLayout, QLabel, QMessageBox, QMenu
from indexed import IndexedOrderedDict

from new.data import Category
from new.ui.desktop import dynamic_data_components
# from new.ui.desktop.custom_generic_components import add_checkbox_in_table_at
from new.ui.desktop.custom_generic_components import add_checkbox_in_table_at

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


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
        self.__layout.addRow("Dynamic Data New Instances", self.__dynamic_instances_table)
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
        else:
            self.__fill_data(category)

            # Add context menu for editing the order of contents
            self.__category_properties_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.__category_properties_table.customContextMenuRequested.connect(self.__create_content_context_menu)

    def __fill_data(self, category: Category):
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

        # Dynamic data instances table
        self.__dynamic_instances_table.blockSignals(True)
        self.__dynamic_instances_table.setRowCount(len(category.dynamic_data_initialisations))
        dynamic_data_components.fill_dynamic_instantiations_table(self.__dynamic_instances_table, category.dynamic_data_initialisations)
        self.__dynamic_instances_table.blockSignals(False)

        # Dynamic data modifications table
        self.__dynamic_data_table.blockSignals(True)
        self.__dynamic_data_table.setRowCount(len(category.dynamic_data_operations))
        dynamic_data_components.fill_dynamic_modifications_table(self.__dynamic_data_table, category.dynamic_data_operations)
        self.__dynamic_data_table.blockSignals(False)

        # Dynamic data modifications table
        self.__dynamic_data_templates_table.blockSignals(True)
        self.__dynamic_data_templates_table.setRowCount(len(category.dynamic_data_operation_templates))
        dynamic_data_components.fill_dynamic_modifications_table(self.__dynamic_data_templates_table, category.dynamic_data_operation_templates)
        self.__dynamic_data_templates_table.blockSignals(False)

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
        if self.generated_category is not None and \
                self.__category is not None and \
                not set(self.__category.contents.keys()).issubset(self.generated_category.contents.keys()):
            result = QMessageBox.question(
                self,
                "Are you sure?",
                "You have removed a category field. This will result in all associated data being deleted. Are you sure?",
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
        menu.addAction(insert_above_action)
        menu.addAction(insert_row_below_action)
        menu.addAction(delete_row_action)
        menu.addAction(move_row_up_action)
        menu.addAction(move_row_down_action)
        menu.exec(self.__category_properties_table.mapToGlobal(pos))

    def __insert_row_above(self, row):
        # Add our instruction
        self.edit_instructions.append(("INSERT_AT", row))

        # Perform action @ GUI
        self.__category_properties_table.insertRow(row)
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


def add_or_edit_category(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', category: Category | None):
    # Build a dialog to edit the current category information
    edit_category_dialog = CategoryDialog(engine, category)
    edit_category_dialog.exec()

    # Validate dialog output
    if not edit_category_dialog.success:
        return

    # Add our new category
    if category is None:
        engine.add_category(edit_category_dialog.generated_category)

    # Edit the category in our engine
    else:
        new_category = edit_category_dialog.generated_category
        new_category.unique_id = category.unique_id
        engine.edit_category(new_category, edit_category_dialog.edit_instructions)

    # Trigger a refresh of the UI
    parent.handle_update()


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
