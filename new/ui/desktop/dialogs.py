from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QLineEdit, QPushButton, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QMessageBox, QLabel, QMenu, QComboBox, QPlainTextEdit, QWidget, QVBoxLayout, QScrollArea, QHBoxLayout
from indexed import IndexedOrderedDict

from new.data import Category, Output, Entry
from new.ui.desktop import widget_factories

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine


def add_checkbox_in_table_at(table, row_index, column_index=1, state=False, callback=None):
    check_box = QCheckBox()

    # Handle the initial state
    if state:
        check_box.setCheckState(Qt.CheckState.Checked)
    else:
        check_box.setCheckState(Qt.CheckState.Unchecked)

    # Handle a callback
    if callback is not None:
        check_box.stateChanged.connect(callback)

    table.setCellWidget(row_index, column_index, check_box)


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
        self.__character_categories_table.setHorizontalHeaderItem(0, QTableWidgetItem("Categories"))
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
            self.success = QMessageBox.question(self, "Are you sure?", "You have removed a category from a character. This will result in all associated entries from that character+category combination from being deleted. Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
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

        # Dynamic data instancing
        self.__dynamic_instances_table = QTableWidget()
        self.__dynamic_instances_table.setColumnCount(3)
        self.__dynamic_instances_table.setHorizontalHeaderItem(0, QTableWidgetItem("Dynamic Data Key"))
        self.__dynamic_instances_table.setHorizontalHeaderItem(1, QTableWidgetItem("Initial Value"))
        self.__dynamic_instances_table.setHorizontalHeaderItem(2, QTableWidgetItem("Initial Value Format"))
        self.__dynamic_instances_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.__dynamic_instances_table.setRowCount(1)
        self.__dynamic_instances_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
        self.__dynamic_instances_table.cellChanged.connect(self.__handle_dynamic_data_instances_cell_changed_callback)

        # Dynamic data modifications
        self.__dynamic_modifications_table = QTableWidget()
        self.__dynamic_modifications_table.setColumnCount(3)
        self.__dynamic_modifications_table.setHorizontalHeaderItem(0, QTableWidgetItem("Modification Target"))
        self.__dynamic_modifications_table.setHorizontalHeaderItem(1, QTableWidgetItem("Modification Type"))
        self.__dynamic_modifications_table.setHorizontalHeaderItem(2, QTableWidgetItem("Modification Calculation (String Representation)"))
        self.__dynamic_modifications_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.__dynamic_modifications_table.setRowCount(1)
        self.__dynamic_modifications_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
        self.__dynamic_modifications_table.cellChanged.connect(self.__handle_dynamic_data_modifications_cell_changed_callback)

        # Dynamic modification templating
        self.__dynamic_modification_templates_table = QTableWidget()
        self.__dynamic_modification_templates_table.setColumnCount(3)
        self.__dynamic_modification_templates_table.setHorizontalHeaderItem(0, QTableWidgetItem("Modification Target"))
        self.__dynamic_modification_templates_table.setHorizontalHeaderItem(1, QTableWidgetItem("Modification Type"))
        self.__dynamic_modification_templates_table.setHorizontalHeaderItem(2, QTableWidgetItem("Modification Calculation (String Representation)"))
        self.__dynamic_modification_templates_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.__dynamic_modification_templates_table.setRowCount(1)
        self.__dynamic_modification_templates_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
        self.__dynamic_modification_templates_table.cellChanged.connect(self.__handle_dynamic_data_modification_templates_cell_changed_callback)

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
        self.__layout.addRow("Dynamic Data Modifications", self.__dynamic_modifications_table)
        self.__layout.addRow("", QLabel("The next section deals with dynamic data modification templates for all entries. Only use if you understand what is going on."))
        self.__layout.addRow("Dynamic Data Modification Templates", self.__dynamic_modification_templates_table)
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
        for i, (k, v) in enumerate(category.dynamic_data_initialisations.items()):
            self.__dynamic_instances_table.setItem(i, 0, QTableWidgetItem(k))
            self.__dynamic_instances_table.setItem(i, 1, QTableWidgetItem(str(v)))
            data_type_selector = widget_factories.create_dynamic_data_type_selector()
            if isinstance(v, str):
                data_type_selector.setCurrentText("STRING")
            elif isinstance(v, int):
                data_type_selector.setCurrentText("INT")
            else:
                data_type_selector.setCurrentText("FLOAT")
            self.__dynamic_instances_table.setItem(i, 2, QTableWidgetItem(data_type_selector))
        self.__dynamic_instances_table.blockSignals(False)

        # Dynamic data modifications table
        self.__dynamic_modifications_table.blockSignals(True)
        self.__dynamic_modifications_table.setRowCount(len(category.dynamic_data_operations))
        for i, (k, (o, t)) in enumerate(category.dynamic_data_operations.items()):
            self.__dynamic_modifications_table.setItem(i, 0, QTableWidgetItem(k))
            self.__dynamic_modifications_table.setItem(i, 2, QTableWidgetItem(o))
            operation_type_selector = widget_factories.create_dynamic_operation_type_selector()
            operation_type_selector.setCurrentText(t)
            self.__dynamic_modifications_table.setItem(i, 1, QTableWidgetItem(operation_type_selector))
        self.__dynamic_modifications_table.blockSignals(False)

        # Dynamic data modifications table
        self.__dynamic_modification_templates_table.blockSignals(True)
        self.__dynamic_modification_templates_table.setRowCount(len(category.dynamic_data_operation_templates))
        for i, (k, (o, t)) in enumerate(category.dynamic_data_operation_templates.items()):
            self.__dynamic_modification_templates_table.setItem(i, 0, QTableWidgetItem(k))
            self.__dynamic_modification_templates_table.setItem(i, 2, QTableWidgetItem(o))
            operation_type_selector = widget_factories.create_dynamic_operation_type_selector()
            operation_type_selector.setCurrentText(t)
            self.__dynamic_modification_templates_table.setItem(i, 1, QTableWidgetItem(operation_type_selector))
        self.__dynamic_modification_templates_table.blockSignals(False)

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

    def __handle_dynamic_data_instances_cell_changed_callback(self, row, column):
        # Only interested in the primary column updates
        if column != 0:
            return

        # Ensure that something was actually added, so we aren't adding rows willy-nilly, also that we are editing the last row
        item = self.__dynamic_instances_table.item(row, 0)
        if item is None:
            return
        item = item.text()
        if item == "":
            return
        target_row = row + 1
        if self.__dynamic_instances_table.rowCount() != target_row:
            return

        # Add a row
        self.__dynamic_instances_table.blockSignals(True)
        self.__dynamic_instances_table.insertRow(target_row)
        self.__dynamic_instances_table.setVerticalHeaderItem(target_row, QTableWidgetItem(str(target_row)))
        self.__dynamic_instances_table.setItem(target_row, 2, QTableWidgetItem(widget_factories.create_dynamic_data_type_selector()))
        self.__dynamic_instances_table.blockSignals(False)

    def __handle_dynamic_data_modifications_cell_changed_callback(self, row, column):
        # Only interested in the primary column updates
        if column != 0:
            return

        # Ensure that something was actually added, so we aren't adding rows willy-nilly, also that we are editing the last row
        item = self.__dynamic_modifications_table.item(row, 0)
        if item is None:
            return
        item = item.text()
        if item == "":
            return
        target_row = row + 1
        if self.__dynamic_modifications_table.rowCount() != target_row:
            return

        # Add a row
        self.__dynamic_modifications_table.blockSignals(True)
        self.__dynamic_modifications_table.insertRow(target_row)
        self.__dynamic_modifications_table.setVerticalHeaderItem(target_row, QTableWidgetItem(str(target_row)))
        self.__dynamic_modifications_table.setItem(target_row, 1, QTableWidgetItem(widget_factories.create_dynamic_operation_type_selector()))
        self.__dynamic_modifications_table.blockSignals(False)

    def __handle_dynamic_data_modification_templates_cell_changed_callback(self, row, column):
        # Only interested in the primary column updates
        if column != 0:
            return

        # Ensure that something was actually added, so we aren't adding rows willy-nilly, also that we are editing the last row
        item = self.__dynamic_modification_templates_table.item(row, 0)
        if item is None:
            return
        item = item.text()
        if item == "":
            return
        target_row = row + 1
        if self.__dynamic_modification_templates_table.rowCount() != target_row:
            return

        # Add a row
        self.__dynamic_modification_templates_table.blockSignals(True)
        self.__dynamic_modification_templates_table.insertRow(target_row)
        self.__dynamic_modification_templates_table.setVerticalHeaderItem(target_row, QTableWidgetItem(str(target_row)))
        self.__dynamic_modification_templates_table.setItem(target_row, 1, QTableWidgetItem(widget_factories.create_dynamic_operation_type_selector()))
        self.__dynamic_modification_templates_table.blockSignals(False)

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

        # Build our dynamic data new instances
        new_instances = dict()
        for row_index in range(self.__dynamic_instances_table.rowCount()):
            item = self.__dynamic_instances_table.item(row_index, 0)

            # Continue if empty
            if item is None:
                continue
            dynamic_key = item.text()
            if dynamic_key == "":
                continue

            type = self.__dynamic_instances_table.item(row_index, 2).currentText()
            try:
                match type:
                    case "STRING":
                        new_instances[dynamic_key] = self.__dynamic_instances_table.item(row_index, 1).text()
                    case "INT":
                        new_instances[dynamic_key] = int(self.__dynamic_instances_table.item(row_index, 1).text())
                    case "FLOAT":
                        new_instances[dynamic_key] = float(self.__dynamic_instances_table.item(row_index, 1).text())
                    case _:
                        raise Exception("Not a valid type string")
            except Exception as e:
                self.__handle_cancel_callback()
                return

        # Build our dynamic data new instances
        modifications = dict()
        for row_index in range(self.__dynamic_modifications_table.rowCount()):
            item = self.__dynamic_modifications_table.item(row_index, 0)

            # Continue if empty
            if item is None:
                continue
            dynamic_key = item.text()
            if dynamic_key == "":
                continue

            operation = self.__dynamic_modifications_table.item(row_index, 1).text()
            type = self.__dynamic_modifications_table.item(row_index, 2).currentText()
            modifications[dynamic_key] = (operation, type)

        # Build our dynamic data new instances
        template_modifications = dict()
        for row_index in range(self.__dynamic_modification_templates_table.rowCount()):
            item = self.__dynamic_modification_templates_table.item(row_index, 0)

            # Continue if empty
            if item is None:
                continue
            dynamic_key = item.text()
            if dynamic_key == "":
                continue

            operation = self.__dynamic_modification_templates_table.item(row_index, 1).text()
            type = self.__dynamic_modification_templates_table.item(row_index, 2).currentText()
            template_modifications[dynamic_key] = (operation, type)

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
                dynamic_data_initialisations=new_instances,
                dynamic_data_operations=modifications,
                dynamic_data_operation_templates=template_modifications
            )

        # Check if an item has been removed from our original input list
        if self.generated_category is not None and \
                self.__category is not None and \
                not set(self.__category.contents.keys()).issubset(self.generated_category.contents.keys()):
            self.success = QMessageBox.question(
                self,
                "Are you sure?",
                "You have removed a category field. This will result in all associated data being deleted. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
            )
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


class OutputDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine', output: Output):
        super(OutputDialog, self).__init__()
        self.__engine = engine
        self.output = output
        self.success = False

        # Form components
        self.__name_field = QLineEdit()
        self.__target_gsheet = QComboBox()
        self.__target_gsheet.addItems(self.__engine.get_unassigned_gsheets())
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Results view
        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view.setLayout(self.__results_view_layout)
        self.__results_view_scroll = QScrollArea()
        self.__results_view_scroll.setWidget(self.__results_view)
        self.__results_view_scroll.setWidgetResizable(True)

        # Form
        self.__layout = QFormLayout()
        self.__layout.addRow("Unique Name:", self.__name_field)
        self.__layout.addRow("Target GSheet:", self.__target_gsheet)
        self.__layout.addRow("Applicable Entries:", self.__results_view_scroll)
        self.__layout.addRow(self.__cancel_button, self.__done_button)
        self.setLayout(self.__layout)
        self.setMinimumWidth(640)

        # General
        if output.name == "MOCK":
            self.setWindowTitle("New Output.")

        else:
            self.setWindowTitle("Edit Output")
            self.__name_field.setText(output.name)

            # Assign Gsheets info - it won't actually contain our target gsheet as that will count as 'assigned' by the engine
            # We will need to add ours in manually
            self.__target_gsheet.blockSignals(True)
            self.__target_gsheet.addItem(output.gsheet_target)
            index = self.__target_gsheet.findText(output.gsheet_target)
            self.__target_gsheet.setCurrentIndex(index)
            self.__target_gsheet.blockSignals(False)

        # Draw contents
        self.__draw_results()

    def __draw_results(self):
        # Clear our current results
        for i in reversed(range(self.__results_view_layout.count())):
            w = self.__results_view_layout.itemAt(i).widget()
            self.__results_view_layout.removeWidget(w)
            w.deleteLater()

        # Render the entries that are actually included in our output first
        max_index = len(self.output.members)
        for current_index, result_id in enumerate(self.output.members):
            result = self.__engine.get_entry_by_id(result_id)
            self.__draw_entry(max_index, current_index, result, True)

        # Render the entries that are not in our output
        max_index = len(self.output.ignored)
        for current_index, result_id in enumerate(self.output.ignored):
            result = self.__engine.get_entry_by_id(result_id)
            self.__draw_entry(max_index, current_index, result, False)

    def __draw_entry(self, max_index: int, current_index: int, entry: Entry, state: bool):
        character = self.__engine.get_character_by_id(entry.character_id)
        category = self.__engine.get_category_by_id(entry.category_id)
        entry_index = self.__engine.get_entry_index_in_history(entry.unique_id)

        # Form
        entry_form = QWidget()
        entry_form_layout = QFormLayout()
        widget_factories.create_entry_form(entry_form_layout, character, category, entry, entry_index)
        entry_form.setLayout(entry_form_layout)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        move_up_button = QPushButton("Move Entry Up")
        if current_index > 0:
            move_up_button.clicked.connect(self.__handle_move_up_callback, current_index, state)
        entry_controls_layout.addWidget(move_up_button)
        move_down_button = QPushButton("Move Entry Down")
        if current_index < max_index - 1:
            move_down_button.clicked.connect(self.__handle_move_down_callback, current_index, state)
        entry_controls_layout.addWidget(move_down_button)
        enabled_checkbox = QCheckBox("Entry In Output?")
        enabled_checkbox.setChecked(state)
        enabled_checkbox.clicked.connect(self.__handle_entry_changed_state_callback, current_index, entry.unique_id, state)
        entry_controls_layout.addWidget(enabled_checkbox)
        spacer = QWidget()
        entry_controls_layout.addWidget(spacer)
        entry_controls_layout.setStretchFactor(spacer, 100)
        entry_controls_layout.setContentsMargins(0, 0, 0, 0)
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

    def __handle_move_up_callback(self, current_index: int, state: bool):
        if state:
            target_list = self.output.members
        else:
            target_list = self.output.ignored
        target_list.insert(current_index - 1, target_list.pop(current_index))

    def __handle_move_down_callback(self, current_index: int, state: bool):
        if state:
            target_list = self.output.members
        else:
            target_list = self.output.ignored
        target_list.insert(current_index + 1, target_list.pop(current_index))

    def __handle_entry_changed_state_callback(self, current_index: int, state: bool):
        if state:
            source = self.output.members
            target = self.output.ignored
        else:
            source = self.output.ignored
            target = self.output.members
        entry_id = source.pop(current_index)
        target.append(entry_id)

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        outputs = self.__engine.get_outputs()
        names = [o.name for o in outputs]

        # Bail if there is no name or it is not unique
        name = self.__name_field.text()
        if name is None or name == "" or name in names:
            self.success = False
            self.close()
            return
        self.output.name = name

        self.output.gsheet_target = self.__target_gsheet.currentText()
        self.success = True
        self.close()


class OutputSelectorDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self.__engine = engine
        self.success = False
        self.view_id = None

        # Character selector
        self.__view_selector = QComboBox()
        self.__view_selector.addItem("Please Select A View")

        # Fill in our character data
        for index, view in enumerate(self.__engine.get_outputs()):
            self.__view_selector.addItem(view.name)
            self.__view_selector.setItemData(index + 1, view.unique_id, Qt.ItemDataRole.UserRole)

        # Buttons
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Layout
        self.__layout = QFormLayout()
        self.__layout.addRow("View:", self.__view_selector)
        self.__layout.addRow(self.__cancel_button, self.__done_button)
        self.setLayout(self.__layout)

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        self.view_id = self.__view_selector.currentData()
        self.success = True if self.view_id is not None else False
        self.close()


class EntryDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine', entry: Entry | None, editing: bool = False):
        super(EntryDialog, self).__init__()
        self.__engine = engine
        if entry is None:
            self.entry = Entry("MOCK", "MOCK", list())
            self.__new_entry = True
        else:
            self.entry = entry
            self.__new_entry = False
        self.__editing = editing
        self.success = False

        # Preallocs
        self.__character_selector = None
        self.__character_id = None
        self.__category_selector = None
        self.__category_id = None
        self.__results = list()

        # Static Buttons
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Layout
        self.__layout = QFormLayout()
        self.setLayout(self.__layout)

        # Force update
        self.__handle_update()

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        # Check our character
        if self.__character_id is None or self.__character_id == "" or self.__character_id == "None Selected":
            self.__handle_cancel_callback()
            return

        # Check our category
        if self.__category_id is None or self.__category_id == "" or self.__category_id == "None Selected":
            self.__handle_cancel_callback()
            return

        # Gather our data using our callback results
        payload = list()
        for index, item in enumerate(self.__results):
            if isinstance(item, QLineEdit):
                payload.append(item.text())
            elif isinstance(item, QPlainTextEdit):
                payload.append(item.toPlainText())
        is_disabled = self.__results[-1].isChecked()

        # Apply to THIS entry
        self.entry.character_id = self.__character_id
        self.entry.category_id = self.__category_id
        self.entry.data = payload
        self.entry.is_disabled = is_disabled

        # Flags
        self.success = True
        self.close()

    def __handle_update(self):
        # Remove the rows we no longer need
        row_count = self.__layout.rowCount()
        stored_rows = list()
        for row in reversed(range(0, row_count)):
            # Do not delete our headers (for new entries only) or our buttons
            if row == row_count - 1 or (self.__new_entry and row < 2):
                stored_rows.append(self.__layout.takeRow(row))
            else:
                self.__layout.removeRow(row)

        # Depending on our state, we need to display different things
        if self.__new_entry:
            self.__handle_new_entry_update()

        else:
            self.__character_id = self.entry.character_id
            self.__category_id = self.entry.category_id

        # If we have everything we need for the form data
        if self.__character_id is not None and self.__category_id is not None:

            # Fetch data
            character = self.__engine.get_character_by_id(self.__character_id)
            category = self.__engine.get_category_by_id(self.__category_id)
            if self.__editing:
                index = self.__engine.get_entry_index_in_history(self.entry.unique_id)
            else:
                index = self.__engine.get_current_history_index()

            # Add our entry to the form if possible
            self.__results = widget_factories.create_entry_form(self.__layout, character, category, self.entry, index, not self.__new_entry, False)

        # Add our buttons
        self.__layout.addRow(self.__cancel_button, self.__done_button)

    def __handle_new_entry_update(self):
        # First build
        if self.__character_selector is None:
            self.__character_selector = QComboBox()
            self.__character_selector.currentTextChanged.connect(self.__handle_update)
            self.__character_selector.blockSignals(True)
            self.__character_selector.addItem("Please Select a Character")

            # Fill in our character data
            for index, character in enumerate(self.__engine.get_characters()):
                self.__character_selector.addItem(character.name)
                self.__character_selector.setItemData(index + 1, character.unique_id, Qt.ItemDataRole.UserRole)

            self.__character_selector.blockSignals(False)

        if self.__category_selector is None:
            self.__category_selector = QComboBox()
            self.__category_selector.currentTextChanged.connect(self.__handle_update)
            self.__category_selector.blockSignals(True)
            self.__category_selector.addItem("Please Select a Character First")
            self.__category_selector.blockSignals(False)

        # The fields are always present
        self.__layout.addRow("Character:", self.__character_selector)
        self.__layout.addRow("Category:", self.__category_selector)

        # If our choice of character has changed
        current_character_id = self.__character_selector.currentData()
        if current_character_id != self.__character_id:
            self.__category_selector.blockSignals(True)
            self.__category_selector.clear()
            self.__character_id = current_character_id
            if current_character_id is None:
                self.__category_selector.addItem("Please Select a Character First")
            else:
                self.__add_categories()
            self.__category_selector.blockSignals(False)

        # Only continue if category is selected - No need to check cache here, just grab and assign no matter what
        if self.__category_selector.currentData() is not None:
            self.__category_id = self.__category_selector.currentData()
        else:
            self.__category_id = None

    def __add_categories(self):
        self.__category_selector.addItem("Please Select a Category")

        categories = self.__engine.get_categories_for_character_id(self.__character_id)
        for index, category_id in enumerate(categories):
            category = self.__engine.get_category_by_id(category_id)

            # Ignore singleton categories that already have associated data
            if category.single_entry_only:
                state = self.__engine.get_entries_for_character_and_category_at_current_history_index(self.__character_id, category_id)
                if state is not None and len(state) != 0:
                    continue

            # Add them to our drop down
            self.__category_selector.addItem(category.name)
            self.__category_selector.setItemData(index + 1, category.unique_id, Qt.ItemDataRole.UserRole)
