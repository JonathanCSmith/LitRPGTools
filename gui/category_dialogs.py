from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QHeaderView, QMenu, QCheckBox, QComboBox
from PyQt6.uic.properties import QtGui

from data.categories import CategoryProperty, Category

if TYPE_CHECKING:
    from main import LitRPGTools


def add_check_box_at(category_properties_table, index, state=False):
    check_box = QTableWidgetItem()
    check_box.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
    if state:
        check_box.setCheckState(Qt.CheckState.Checked)
    else:
        check_box.setCheckState(Qt.CheckState.Unchecked)
    category_properties_table.setItem(index, 1, check_box)


class CategoryDialog(QDialog):
    def __init__(self, category=None):
        super().__init__()
        self.category = category

        # General
        if category is None:
            self.setWindowTitle("New Category")
        else:
            self.setWindowTitle("Edit Category")

        # Form components
        self.category_name = QLineEdit()
        self.category_properties_table = QTableWidget()
        self.category_properties_table.setColumnCount(2)
        self.category_properties_table.setHorizontalHeaderItem(0, QTableWidgetItem("Property Text"))
        self.category_properties_table.setHorizontalHeaderItem(1, QTableWidgetItem("Requires Large Input Text"))
        self.category_properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.category_properties_table.setRowCount(1)
        self.category_properties_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
        self.category_properties_table.cellChanged.connect(self.cell_changed)
        self.print_to_overview_button = QCheckBox()
        self.can_change_over_time = QCheckBox()
        self.is_singleton = QCheckBox()
        self.notes_only = QCheckBox()
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Data
        if self.category is not None and len(self.category.get_properties()) > 0:
            self.category_name.setText(self.category.get_name())

            # Loop through our categories
            self.category_properties_table.blockSignals(True)
            category_properties = self.category.get_properties()
            index = None
            for index in range(len(category_properties)):
                category_property = category_properties[index]

                # Only add rows AFTER the first as it should already exist
                if index != 0:
                    self.category_properties_table.insertRow(index)

                # Add the data
                self.category_properties_table.setItem(index, 0, QTableWidgetItem(category_property.get_property_name()))
                add_check_box_at(self.category_properties_table, index, state=category_property.requires_large_input())

            # Add extra row blank for user edit
            index += 1
            self.category_properties_table.insertRow(index)
            self.category_properties_table.setItem(index, 0, QTableWidgetItem(""))
            add_check_box_at(self.category_properties_table, index)
            self.category_properties_table.blockSignals(False)

        else:
            self.category_properties_table.setItem(0, 0, QTableWidgetItem(""))
            add_check_box_at(self.category_properties_table, 0)

        # Add in our history
        if self.category is None:
            self.history_entry = QLineEdit()
            self.update_history_entry = QLineEdit()
        else:
            self.history_entry = QLineEdit(self.category.get_new_history_entry())
            self.update_history_entry = QLineEdit(self.category.get_update_history_entry())

        # Form
        self.layout = QFormLayout()
        self.layout.addRow("Category Name", self.category_name)
        self.layout.addRow("Category Properties", self.category_properties_table)
        self.layout.addRow("", QLabel("For the next section, please input your 'display' string for each situation. Use {0} to insert entry data from the 1st row (row headers are correct)."))
        self.layout.addRow("New Entry History Summary:", self.history_entry)
        self.layout.addRow("Update Entry History Summary:", self.update_history_entry)
        self.layout.addRow("Print Category to Overview?", self.print_to_overview_button)
        self.layout.addRow("Can entries change over time?", self.can_change_over_time)
        self.layout.addRow("Is Singleton?", self.is_singleton)
        self.layout.addRow("Notes Only (No Output to Sheets)?", self.notes_only)
        self.layout.addRow("", self.done_button)
        self.setLayout(self.layout)
        self.setMinimumWidth(640)

        self.viable = False

    def cell_changed(self, row, column):
        if column != 0:
            return

        item = self.category_properties_table.item(row, 0)
        if item is None:
            return
        item = item.text()

        target_row = row + 1
        if item != "" and self.category_properties_table.rowCount() == target_row:
            self.category_properties_table.blockSignals(True)
            self.category_properties_table.insertRow(target_row)
            self.category_properties_table.setVerticalHeaderItem(target_row, QTableWidgetItem(str(target_row)))
            add_check_box_at(self.category_properties_table, target_row)
            self.category_properties_table.blockSignals(False)

    def get_data(self):
        properties = list()
        for row_index in range(self.category_properties_table.rowCount()):
            item = self.category_properties_table.item(row_index, 0)
            if item is None:
                continue
            property_name = item.text()
            if property_name == "":
                continue

            property_requires_large_input = self.category_properties_table.item(row_index, 1).checkState() == Qt.CheckState.Checked
            prop = CategoryProperty(property_name, property_requires_large_input)
            properties.append(prop)

        # Empty == NOOP
        if len(properties) == 0:
            return None

        return Category(self.category_name.text(), properties, self.history_entry.text(), self.update_history_entry.text(), self.print_to_overview_button.isChecked(), self.can_change_over_time.isChecked(), self.is_singleton.isChecked(), self.notes_only.isChecked())

    def handle_done(self, *args):
        self.viable = True
        self.close()


class EditCategoryDialog(QDialog):
    def __init__(self, category):
        super().__init__()
        self.setWindowTitle("Edit Category")

        # Category Properties
        self.category = category
        self.category_properties = self.category.get_properties()

        # Outcome handlers
        self.edit_instructions = []

        # Form components
        self.category_name = QLineEdit()
        self.category_properties_table = QTableWidget()
        self.category_properties_table.setColumnCount(2)
        self.category_properties_table.setHorizontalHeaderItem(0, QTableWidgetItem("Property Text"))
        self.category_properties_table.setHorizontalHeaderItem(1, QTableWidgetItem("Requires Large Input Text"))
        self.category_properties_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.category_properties_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
        self.category_properties_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.category_properties_table.customContextMenuRequested.connect(self.create_context_menu)
        self.print_to_overview_button = QCheckBox()
        self.print_to_overview_button.setChecked(category.get_print_to_overview())
        self.can_change_over_time = QCheckBox()
        self.can_change_over_time.setChecked(category.can_change_over_time)
        self.notes_only = QCheckBox()
        self.notes_only.setChecked(category.notes_only)
        self.is_singleton = QCheckBox()
        self.is_singleton.setChecked(category.is_singleton)
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Data
        self.category_name.setText(self.category.get_name())

        # Loop through our categories
        self.draw_table()

        # Add in our history
        self.history_entry = QLineEdit(self.category.get_new_history_entry())
        self.update_history_entry = QLineEdit(self.category.get_update_history_entry())

        # Form
        self.layout = QFormLayout()
        self.layout.addRow("Category Name", self.category_name)
        self.layout.addRow("Category Properties", self.category_properties_table)
        self.layout.addRow("", QLabel("For the next section, please input your 'display' string for each situation. Use {0} to insert entry data from the 1st row (row headers are correct)."))
        self.layout.addRow("New Entry History Summary:", self.history_entry)
        self.layout.addRow("Update Entry History Summary:", self.update_history_entry)
        self.layout.addRow("Print Category to Overview?", self.print_to_overview_button)
        self.layout.addRow("Can entries change over time?", self.can_change_over_time)
        self.layout.addRow("Is Singleton?", self.is_singleton)
        self.layout.addRow("Notes Only (No Output to Sheets)?", self.notes_only)
        self.layout.addRow("", self.done_button)
        self.setLayout(self.layout)
        self.setMinimumWidth(640)

        self.viable = False

    def draw_table(self):
        self.category_properties_table.setRowCount(len(self.category_properties))
        self.category_properties_table.blockSignals(True)
        for index in range(len(self.category_properties)):
            category_property = self.category_properties[index]
            self.category_properties_table.setItem(index, 0, QTableWidgetItem(category_property.get_property_name()))
            add_check_box_at(self.category_properties_table, index, state=category_property.requires_large_input())
        self.category_properties_table.blockSignals(False)

    def get_data(self):
        properties = list()
        for row_index in range(self.category_properties_table.rowCount()):
            item = self.category_properties_table.item(row_index, 0)
            if item is None:
                continue
            property_name = item.text()
            if property_name == "":
                continue

            property_requires_large_input = self.category_properties_table.item(row_index, 1).checkState() == Qt.CheckState.Checked
            prop = CategoryProperty(property_name, property_requires_large_input)
            properties.append(prop)

        # Empty == NOOP
        if len(properties) == 0:
            return None

        return Category(self.category_name.text(), properties, self.history_entry.text(), self.update_history_entry.text(), self.print_to_overview_button.isChecked(), self.can_change_over_time.isChecked(), self.is_singleton.isChecked(), self.notes_only.isChecked())

    def get_instructions(self):
        return self.edit_instructions

    def handle_done(self, *args):
        self.viable = True
        self.close()

    def create_context_menu(self, pos):
        if self.category_properties_table.itemAt(pos) is None:
            return

        row = self.category_properties_table.itemAt(pos).row()

        # Context menu actions
        insert_above_action = QAction("Insert Row Above", self)
        insert_above_action.triggered.connect(partial(self.insert_row_above, row))
        insert_row_below_action = QAction("Insert Row Below", self)
        insert_row_below_action.triggered.connect(partial(self.insert_row_below, row))
        delete_row_action = QAction("Delete Row", self)
        delete_row_action.triggered.connect(partial(self.delete_row, row))
        move_row_up_action = QAction("Move Row Up", self)
        move_row_up_action.triggered.connect(partial(self.move_row_up, row))
        move_row_down_action = QAction("Move Row Down", self)
        move_row_down_action.triggered.connect(partial(self.move_row_down, row))

        # Menu
        menu = QMenu()
        menu.addAction(insert_above_action)
        menu.addAction(insert_row_below_action)
        menu.addAction(delete_row_action)
        menu.addAction(move_row_up_action)
        menu.addAction(move_row_down_action)
        menu.exec(self.category_properties_table.mapToGlobal(pos))

    def insert_row_above(self, row):
        # Add our instruction
        self.edit_instructions.append(("INSERT_AT", row))

        # Perform action @ GUI
        self.category_properties_table.insertRow(row)
        add_check_box_at(self.category_properties_table, row)

    def insert_row_below(self, row):
        row = row + 1
        self.insert_row_above(row)

    def delete_row(self, row):
        # Add our instruction
        self.edit_instructions.append(("DELETE", row))

        # Perform action @ GUI
        self.category_properties_table.removeRow(row)

    def move_row_up(self, row):
        # Add our instruction
        self.edit_instructions.append(("MOVE UP", row))

        # Perform action @ GUI
        self.category_properties_table.insertRow(row - 1)
        for column in range(self.category_properties_table.columnCount()):
            item = self.category_properties_table.takeItem(row + 1, column)
            if item:
                self.category_properties_table.setItem(row - 1, column, item)
        self.category_properties_table.removeRow(row + 1)

    def move_row_down(self, row):
        # Add our instruction
        self.edit_instructions.append(("MOVE DOWN", row))

        # Perform action @ GUI
        self.category_properties_table.insertRow(row + 1)
        for column in range(self.category_properties_table.columnCount()):
            item = self.category_properties_table.takeItem(row, column)
            if item:
                self.category_properties_table.setItem(row + 1, column, item)
        self.category_properties_table.removeRow(row)


class CategoryAssignmentDialog(QDialog):
    def __init__(self, engine: 'LitRPGTools'):
        super(CategoryAssignmentDialog, self).__init__()
        self.engine = engine

        # Form content
        self.character_selector = QComboBox()
        self.character_selector.addItems(self.engine.get_characters().keys())
        self.character_selector.currentTextChanged.connect(self.character_changed)
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Form layout
        self.form_layout = QFormLayout()
        self.form_layout.addRow("Character:", self.character_selector)
        self.setLayout(self.form_layout)
        self.setMinimumWidth(640)

        self.data = dict()
        self.character_changed()
        self.viable = False

    def character_changed(self):
        all_categories = self.engine.get_categories()
        if len(all_categories) == 0:
            return

        # Get the currently enabled categories
        currently_enabled = self.engine.get_character_categories(self.character_selector.currentText())

        # Delete the form layout contents up to a point - these are updated on the fly so have to use 1 as a hard index
        for row_index in range(1, self.form_layout.rowCount()):
            self.form_layout.removeRow(1)
        self.data = dict()

        # Build the contents
        for category in all_categories:
            box = QCheckBox()
            box.setChecked(category in currently_enabled)
            self.data[category] = box
            self.form_layout.addRow(category, box)

        # Add the done button
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)
        self.form_layout.addRow("Done?", self.done_button)

    def handle_done(self, *args):
        self.viable = True
        self.close()

    def get_character(self):
        return self.character_selector.currentText()

    def get_data(self):
        out = list()

        for category, box in self.data.items():
            if box.isChecked():
                out.append(category)

        return out

