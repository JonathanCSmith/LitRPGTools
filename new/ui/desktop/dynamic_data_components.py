from functools import partial
from typing import Dict, Tuple, TYPE_CHECKING

from PyQt6.QtWidgets import QTableWidgetItem, QTableWidget, QHeaderView, QComboBox, QFormLayout, QWidget, QLabel

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine


class DynamicDataTab(QWidget):
    def __init__(self, engine: 'LitRPGToolsEngine', character_id: str):
        super().__init__()
        self._engine = engine
        self.__character_id = character_id

        # Layout
        self.__layout = QFormLayout()
        self.setLayout(self.__layout)

        # Force update
        self.draw()

    def draw(self):
        dynamic_data = self._engine.get_dynamic_data_for_current_index_and_character_id(self.__character_id)
        if dynamic_data is None:
            return

        # Remove old data
        for row in range(self.__layout.rowCount()):
            self.__layout.removeRow(0)

        # Print our dynamic data
        for k, v in dynamic_data.items():
            self.__layout.addRow(k, QLabel(str(v)))


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
    table.setCellWidget(target_row, 1, create_dynamic_operation_type_selector())
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
        operation = table.item(row_index, 2).text()
        operation = operation.replace("\"", "'")
        modifications[dynamic_key] = (type, operation)
    return modifications


def create_dynamic_data_table(readonly: bool = False) -> QTableWidget:
    dynamic_modifications_table = QTableWidget()
    dynamic_modifications_table.setColumnCount(3)
    dynamic_modifications_table.setHorizontalHeaderItem(0, QTableWidgetItem("Modification Target"))
    dynamic_modifications_table.setHorizontalHeaderItem(1, QTableWidgetItem("Modification Type"))
    dynamic_modifications_table.setHorizontalHeaderItem(2, QTableWidgetItem("Modification Calculation (String Representation)"))
    dynamic_modifications_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    dynamic_modifications_table.setRowCount(0)
    dynamic_modifications_table.setVerticalHeaderItem(0, QTableWidgetItem("0"))
    if readonly:
        dynamic_modifications_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    else:
        dynamic_modifications_table.cellChanged.connect(partial(handle_dynamic_data_table_cell_changed_callback, dynamic_modifications_table))
    return dynamic_modifications_table


def fill_dynamic_modifications_table(table: QTableWidget, data: Dict[str, Tuple[str, str]], readonly: bool = False):
    row_count = len(data)
    if not readonly:
        row_count += 1

    # Remove old junk and preallocate rows
    while table.rowCount() > 0:
        table.removeRow(0)

    # Set our table size to existing data count + 1 (for new row info).
    table.setRowCount(row_count)

    # Handle existing data - if none, it won't operate so is fine
    for counter, (k, (t, o)) in enumerate(data.items()):
        table.setItem(counter, 0, QTableWidgetItem(k))
        data_type_selector = create_dynamic_operation_type_selector()
        data_type_selector.setCurrentText(t)
        if readonly:
            data_type_selector.setEnabled(False)
        table.setCellWidget(counter, 1, data_type_selector)
        table.setItem(counter, 2, QTableWidgetItem(o))

    # Extra row for new entries
    if not readonly:
        dynamic_modification_type_selector = create_dynamic_operation_type_selector()
        table.setCellWidget(row_count - 1, 1, dynamic_modification_type_selector)


def create_dynamic_operation_type_selector() -> QComboBox:
    combo_box = QComboBox()
    combo_box.addItems(["ASSIGN STRING", "ASSIGN INTEGER", "ASSIGN FLOAT", "ADD INTEGER", "ADD FLOAT", "SUBTRACT INTEGER", "SUBTRACT FLOAT", "MULTIPLY INTEGER", "MULTIPLY FLOAT", "DIVIDE INTEGER", "DIVIDE FLOAT"])
    return combo_box
