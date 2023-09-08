from functools import partial
from typing import Dict, Tuple, TYPE_CHECKING

from PyQt6.QtCore import Qt, QPersistentModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QTableWidgetItem, QTableWidget, QHeaderView, QComboBox, QFormLayout, QWidget, QLabel, QScrollArea, QVBoxLayout, QCheckBox, QHBoxLayout, QMenu, QStyledItemDelegate, QLineEdit

from desktop.generic_components import LessIntrusiveComboBox

if TYPE_CHECKING:
    from data_manager import LitRPGToolsEngine
    from desktop.gui import LitRPGToolsDesktopGUI


class DynamicDataTab(QWidget):
    def __init__(self, engine: 'LitRPGToolsEngine', character_id: str):
        super().__init__()
        self._engine = engine
        self.__character_id = character_id

        # Toggle button
        self.__toggle_private = False
        self.__toggle_private_button = QCheckBox()
        self.__toggle_private_button.setChecked(False)
        self.__toggle_private_button.clicked.connect(self.__handle_toggle_private_callback)
        self.__toggle_private_layout = QHBoxLayout()
        self.__toggle_private_layout.addWidget(QLabel("Show Private:"))
        self.__toggle_private_layout.addWidget(self.__toggle_private_button)
        self.__toggle_private_layout.addStretch()
        # self.__toggle_private_layout.setContentsMargins(0, 0, 0, 0)
        self.__toggle_private_widget = QWidget()
        self.__toggle_private_widget.setLayout(self.__toggle_private_layout)
        self.__toggle_private_widget.setContentsMargins(0, 0, 0, 0)

        # Layout
        self.__form = QFormLayout()
        self.__form_widget = QWidget()
        self.__form_widget.setLayout(self.__form)
        self.__scroll = QScrollArea()
        self.__scroll.setWidget(self.__form_widget)
        self.__scroll.setWidgetResizable(True)
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__scroll)
        self.__layout.addWidget(self.__toggle_private_widget)
        self.setLayout(self.__layout)

        # Force update
        self.draw()

    def draw(self):
        dynamic_data = self._engine.get_dynamic_data_for_current_index_and_character_id(self.__character_id, self.__toggle_private)
        if dynamic_data is None:
            return

        # Remove old data
        for row in range(self.__form.rowCount()):
            self.__form.removeRow(0)

        # Print our dynamic data
        for k, v in dynamic_data.items():
            self.__form.addRow(k, QLabel(str(v)))

    def __handle_toggle_private_callback(self):
        self.__toggle_private = self.__toggle_private_button.isChecked()
        self.draw()


class ContextMenuDynamicDataItemDelegate(QStyledItemDelegate):
    def __init__(self, root_gui_object: 'LitRPGToolsDesktopGUI', *args):
        super().__init__(*args)
        self.root_gui_object = root_gui_object

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        if isinstance(editor, QLineEdit):
            editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            editor.customContextMenuRequested.connect(self.handle_context_menu)
        return editor

    def handle_context_menu(self, pos):
        editor = self.sender()
        if isinstance(editor, QLineEdit):
            menu = editor.createStandardContextMenu()

            entry_clipboard_data = self.root_gui_object.get_clipboard_item("ENTRY_ID")
            if entry_clipboard_data is not None:
                paste_entry_action = QAction("Paste Clipboard Entry ID")
                paste_entry_action.triggered.connect(partial(self.paste_data_in_cell, editor, entry_clipboard_data))
                menu.addAction(paste_entry_action)

            character_clipboard_data = self.root_gui_object.get_clipboard_item("CHARACTER_ID")
            if character_clipboard_data is not None:
                paste_character_action = QAction("Paste Clipboard Character ID")
                paste_character_action.triggered.connect(partial(self.paste_data_in_cell, editor, character_clipboard_data))
                menu.addAction(paste_character_action)

            menu.exec(editor.mapToGlobal(pos))

    def paste_data_in_cell(self, editor: QLineEdit, data):
        editor.insert(data)


def handle_dynamic_data_table_cell_changed_callback(table, row, column):
    # Only interested in the primary column updates
    if column != 0:
        return

    # Ensure that something was actually added, so we aren't adding rows willy-nilly, also that we are editing the last row
    item = table.item(row, 0)
    if item is None:
        return
    item = item.text()
    if item == "":
        return
    target_row = row + 1
    if table.rowCount() != target_row:
        return

    # Add a row
    table.blockSignals(True)
    table.insertRow(target_row)
    table.setVerticalHeaderItem(target_row, QTableWidgetItem(str(target_row)))
    table.setCellWidget(target_row, 1, create_dynamic_operation_type_selector(table))
    table.setCellWidget(target_row, 2, create_scope_selector(table))
    table.blockSignals(False)


def extract_dynamic_data_table_data(table) -> dict | None:
    modifications = dict()
    for row_index in range(table.rowCount()):
        item = table.item(row_index, 0)

        # Continue if empty
        if item is None:
            continue
        dynamic_key = item.text()
        if dynamic_key == "":
            continue

        type = table.cellWidget(row_index, 1).currentText()
        scope = table.cellWidget(row_index, 2).currentText()
        operation = table.item(row_index, 3).text()
        operation = operation.replace("\"", "")
        modifications[dynamic_key] = (type, scope, operation)
    return modifications


def create_dynamic_data_table(root_gui_object: 'LitRPGToolsDesktopGUI', readonly: bool = False) -> QTableWidget:
    dynamic_modifications_table = QTableWidget()
    delegate = ContextMenuDynamicDataItemDelegate(root_gui_object, dynamic_modifications_table)
    dynamic_modifications_table.setItemDelegate(delegate)
    dynamic_modifications_table.setColumnCount(4)
    dynamic_modifications_table.setHorizontalHeaderItem(0, QTableWidgetItem("Modification Target"))
    dynamic_modifications_table.setHorizontalHeaderItem(1, QTableWidgetItem("Modification Type"))
    dynamic_modifications_table.setHorizontalHeaderItem(2, QTableWidgetItem("Scope"))
    dynamic_modifications_table.setHorizontalHeaderItem(3, QTableWidgetItem("Modification Calculation (String Representation)"))
    dynamic_modifications_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    dynamic_modifications_table.setRowCount(0)
    dynamic_modifications_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
    if readonly:
        dynamic_modifications_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    else:
        dynamic_modifications_table.cellChanged.connect(partial(handle_dynamic_data_table_cell_changed_callback, dynamic_modifications_table))

    # Context menu
    dynamic_modifications_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    dynamic_modifications_table.customContextMenuRequested.connect(partial(create_dynamic_data_table_context_menu, root_gui_object, dynamic_modifications_table, readonly))

    return dynamic_modifications_table


def create_dynamic_data_table_context_menu(root_gui_object: 'LitRPGToolsDesktopGUI', table: QTableWidget, readonly, pos):
    menu = QMenu()

    # Copy behaviour
    copy_action = QAction("Copy Dynamic Data Operations to Clipboard")
    copy_action.triggered.connect(partial(extract_dynamic_data_to_clipboard, root_gui_object, table))
    menu.addAction(copy_action)

    # These are only displayed in specific circumstances
    if not readonly:

        # Paste clipboard behaviour
        clipboard_data = root_gui_object.get_clipboard_item("DYNAMIC_DATA")
        if clipboard_data is not None:
            paste_action = QAction("Paste Clipboard Dynamic Data")
            paste_action.triggered.connect(partial(fill_dynamic_modifications_table, table, clipboard_data, False))
            menu.addAction(paste_action)

        # Get the pertinent row or bail
        if table.itemAt(pos) is not None:
            menu.addSeparator()
            cell = table.itemAt(pos)
            row = cell.row()

            # Create some actions and map these to functions
            insert_above_action = QAction("Insert Row Above")
            insert_above_action.triggered.connect(partial(dynamic_data_table_insert_row, table, row))
            insert_row_below_action = QAction("Insert Row Below")
            insert_row_below_action.triggered.connect(partial(dynamic_data_table_insert_row, table, row + 1))
            move_row_up_action = QAction("Move Row Up")
            move_row_up_action.triggered.connect(partial(dynamic_data_table_move_row_up, table, row))
            move_row_down_action = QAction("Move Row Down")
            move_row_down_action.triggered.connect(partial(dynamic_data_table_move_row_down, table, row))

            # Context menu
            menu.addAction(insert_above_action)
            menu.addAction(insert_row_below_action)
            if row != 0:
                menu.addAction(move_row_up_action)
            if row != table.rowCount() - 1:
                menu.addAction(move_row_down_action)

    menu.exec(table.mapToGlobal(pos))


def paste_data_in_cell(cell, data):
    cell.insertText(data)


def dynamic_data_table_insert_row(table: QTableWidget, row: int):
    table.insertRow(row)
    dynamic_modification_type_selector = create_dynamic_operation_type_selector(table)
    table.setCellWidget(row, 1, dynamic_modification_type_selector)
    scope_selector = create_scope_selector(table)
    table.setCellWidget(row, 2, scope_selector)


def dynamic_data_table_move_row_up(table: QTableWidget, row: int):
    table.insertRow(row - 1)

    # Key
    key_item = table.takeItem(row + 1, 0)
    table.setItem(row - 1, 0, key_item)

    # Data type
    selected_data_type = table.cellWidget(row + 1, 1).currentText()
    data_type_selector = create_dynamic_operation_type_selector(table)
    data_type_selector.setCurrentText(selected_data_type)
    table.setCellWidget(row - 1, 1, data_type_selector)

    # Scope
    selected_scope = table.cellWidget(row + 1, 2).currentText()
    scope_selector = create_scope_selector(table)
    scope_selector.setCurrentText(selected_scope)
    table.setCellWidget(row - 1, 2, scope_selector)

    # Value
    value_item = table.takeItem(row + 1, 3)
    table.setItem(row - 1, 3, value_item)

    table.removeRow(row + 1)


def dynamic_data_table_move_row_down(table: QTableWidget, row: int):
    table.insertRow(row + 2)

    # Key
    key_item = table.takeItem(row, 0)
    table.setItem(row + 2, 0, key_item)

    # Data type
    selected_data_type = table.cellWidget(row, 1).currentText()
    data_type_selector = create_dynamic_operation_type_selector(table)
    data_type_selector.setCurrentText(selected_data_type)
    table.setCellWidget(row + 2, 1, data_type_selector)

    # Scope
    selected_scope = table.cellWidget(row, 2).currentText()
    scope_selector = create_scope_selector(table)
    scope_selector.setCurrentText(selected_scope)
    table.setCellWidget(row + 2, 2, scope_selector)

    # Value
    value_item = table.takeItem(row, 3)
    table.setItem(row + 2, 3, value_item)

    table.removeRow(row)


def extract_dynamic_data_to_clipboard(root_gui_object: 'LitRPGToolsDesktopGUI', table: QTableWidget):
    data = extract_dynamic_data_table_data(table)
    root_gui_object.save_clipboard_item("DYNAMIC_DATA", data)


def fill_dynamic_modifications_table(table: QTableWidget, data: Dict[str, Tuple[str, str, str]], readonly: bool = False):
    row_count = len(data)
    if not readonly:
        row_count += 1

    # Remove old junk and preallocate rows
    while table.rowCount() > 0:
        table.removeRow(0)

    # Set our table size to existing data count + 1 (for new row info).
    table.setRowCount(row_count)

    # Handle existing data - if none, it won't operate so is fine
    for counter, (k, (t, b, o)) in enumerate(data.items()):
        table.setItem(counter, 0, QTableWidgetItem(k))

        data_type_selector = create_dynamic_operation_type_selector(table)
        data_type_selector.setCurrentText(t)

        scope_selector = create_scope_selector(table)
        scope_selector.setCurrentText(b)

        if readonly:
            data_type_selector.setEnabled(False)
            scope_selector.setEnabled(False)

        table.setCellWidget(counter, 1, data_type_selector)
        table.setCellWidget(counter, 2, scope_selector)
        table.setItem(counter, 3, QTableWidgetItem(o))

    # Extra row for new entries
    if not readonly:
        dynamic_modification_type_selector = create_dynamic_operation_type_selector(table)
        table.setCellWidget(row_count - 1, 1, dynamic_modification_type_selector)
        scope_selector = create_scope_selector(table)
        table.setCellWidget(row_count - 1, 2, scope_selector)


def create_dynamic_operation_type_selector(parent) -> LessIntrusiveComboBox:
    combo_box = LessIntrusiveComboBox(parent)
    combo_box.addItems(["ASSIGN STRING", "ASSIGN INTEGER", "ASSIGN FLOAT", "ADD INTEGER", "ADD FLOAT", "SUBTRACT INTEGER", "SUBTRACT FLOAT", "MULTIPLY INTEGER", "MULTIPLY FLOAT", "DIVIDE INTEGER", "DIVIDE FLOAT"])
    return combo_box


def create_scope_selector(parent) -> QComboBox:
    combo_box = LessIntrusiveComboBox(parent)
    combo_box.addItems(["INSTANT", "FINAL", "FUNCTION"])
    return combo_box
