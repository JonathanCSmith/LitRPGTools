from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QComboBox, QPushButton, QWidget, QVBoxLayout, QScrollArea, QFormLayout, QCheckBox, QHBoxLayout, QMessageBox, QLabel, QFrame

from new.data import Output, Entry
from new.ui.desktop import entry_components
from new.ui.desktop.custom_generic_components import Tab
from new.ui.desktop.entry_components import create_entry_form

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


class OutputsTab(Tab):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(OutputsTab, self).__init__(parent, engine)

        # Output selector
        self.__output_selector = QComboBox()
        self.__fill_output_selector()
        self.__output_selector.currentTextChanged.connect(self.__handle_output_selector_changed_callback)

        # Results
        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view.setLayout(self.__results_view_layout)
        self.__results_view_scroll = QScrollArea()
        self.__results_view_scroll.setWidget(self.__results_view)
        self.__results_view_scroll.setWidgetResizable(True)

        # Basic layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__output_selector)
        self.__layout.addWidget(self.__results_view_scroll)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def __fill_output_selector(self):
        self.__output_selector.blockSignals(True)
        current_text = self.__output_selector.currentText()
        self.__output_selector.clear()

        outputs = self._engine.get_outputs()
        for index, output in enumerate(outputs):
            self.__output_selector.addItem(output.name)
            self.__output_selector.setItemData(index, output.unique_id)

        # Restore old selected where relevant
        if current_text is not None:
            self.__output_selector.setCurrentText(current_text)

        self.__output_selector.blockSignals(False)

    def __handle_output_selector_changed_callback(self):
        self.handle_update()

    def handle_update(self):
        self.__fill_output_selector()

        # Clear our current results
        for i in reversed(range(self.__results_view_layout.count())):
            w = self.__results_view_layout.itemAt(i).widget()
            self.__results_view_layout.removeWidget(w)
            w.deleteLater()

        # Get current output
        output_id = self.__output_selector.currentData()
        if output_id is None:
            return
        output = self._engine.get_output_by_id(output_id)
        self.__draw_output(output)

    def __draw_output(self, output: Output):

        # Main widget for the output
        output_widget = QWidget()
        output_widget.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        output_layout = QVBoxLayout()
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_widget.setLayout(output_layout)
        results_view_scroll = QScrollArea()
        results_view_scroll.setWidget(output_widget)
        results_view_scroll.setWidgetResizable(True)

        # Basic props
        basic_props_widget = QWidget()
        basic_props_layout = QFormLayout()
        basic_props_layout.addRow("Output Name:", QLabel(output.name))
        basic_props_layout.addRow("Output Target Gsheet:", QLabel(output.gsheet_target))
        basic_props_widget.setLayout(basic_props_layout)
        output_layout.addWidget(basic_props_widget)

        # Spacer
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        separator.setLineWidth(3)
        separator.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        output_layout.addWidget(separator)

        # Render the entries that are actually included in our output ONLY
        max_index = len(output.members) - 1
        for current_index, result_id in enumerate(output.members):
            entry = self._engine.get_entry_by_id(result_id)
            self.__draw_entry(output_layout, max_index, current_index, entry, True)

        # Render the entries that are actually included in our output ONLY
        max_index = len(output.ignored) - 1
        for current_index, result_id in enumerate(output.ignored):
            entry = self._engine.get_entry_by_id(result_id)
            self.__draw_entry(output_layout, max_index, current_index, entry, False)

        # Controls
        output_controls = QWidget()
        output_controls_layout = QVBoxLayout()
        output_up_button = QPushButton("Move Output End UP")
        output_up_button.clicked.connect(partial(self.__handle_move_output_up_callback, output))
        output_controls_layout.addWidget(output_up_button)
        output_down_button = QPushButton("Move Output End DOWN")
        output_down_button.clicked.connect(partial(self.__handle_move_output_down_callback, output))
        output_controls_layout.addWidget(output_down_button)
        output_edit_button = QPushButton("Edit")
        output_edit_button.clicked.connect(partial(add_or_edit_output, self._engine, self._parent, output))
        output_controls_layout.addWidget(output_edit_button)
        output_delete_button = QPushButton("Delete")
        output_delete_button.clicked.connect(partial(delete_output, self._engine, self._parent, output))
        output_controls_layout.addWidget(output_delete_button)
        output_controls_layout.addStretch()
        # spacer = QWidget()
        # output_controls_layout.addWidget(spacer)
        # output_controls_layout.setStretchFactor(spacer, 100)
        # output_controls_layout.setContentsMargins(0, 0, 0, 0)
        output_controls.setLayout(output_controls_layout)

        # Main container
        main_widget = QWidget()
        main_widget_layout = QHBoxLayout()
        main_widget_layout.addWidget(results_view_scroll)
        main_widget_layout.setStretchFactor(results_view_scroll, 90)
        main_widget_layout.addWidget(output_controls)
        main_widget_layout.setStretchFactor(output_controls, 10)
        main_widget_layout.setContentsMargins(0, 0, 0, 0)
        main_widget.setObjectName("bordered")
        main_widget.setLayout(main_widget_layout)
        self.__results_view_layout.addWidget(main_widget)

    def __draw_entry(self, layout, max_index: int, current_index: int, entry: Entry, state: bool):
        character = self._engine.get_character_by_id(entry.character_id)
        category = self._engine.get_category_by_id(entry.category_id)
        entry_index = self._engine.get_entry_index_in_history(entry.unique_id)

        # Form
        entry_form = QWidget()
        entry_form_layout = QFormLayout()
        create_entry_form(self._engine, entry_form_layout, character, category, entry, entry_index, readonly=True, translate_with_dyanmic_data=True)
        entry_form.setLayout(entry_form_layout)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        edit_entry_button = QPushButton("Edit Entry")
        edit_entry_button.clicked.connect(partial(entry_components.edit_entry, self._engine, self._parent, entry))
        entry_controls_layout.addWidget(entry_controls)
        move_up_button = QPushButton("Move Entry Up")
        if current_index > 0:
            move_up_button.clicked.connect(partial(self.__handle_move_up_callback, entry.unique_id, state))
        entry_controls_layout.addWidget(move_up_button)
        move_down_button = QPushButton("Move Entry Down")
        if current_index < max_index:
            move_down_button.clicked.connect(partial(self.__handle_move_down_callback, entry.unique_id, state))
        entry_controls_layout.addWidget(move_down_button)
        enabled_checkbox = QCheckBox("Entry In Output?")
        enabled_checkbox.setChecked(state)
        enabled_checkbox.clicked.connect(partial(self.__handle_entry_changed_state_callback, entry.unique_id, state))
        entry_controls_layout.addWidget(enabled_checkbox)
        entry_controls_layout.addStretch()
        # spacer = QWidget()
        # entry_controls_layout.addWidget(spacer)
        # entry_controls_layout.setStretchFactor(spacer, 100)
        # entry_controls_layout.setContentsMargins(0, 0, 0, 0)
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
        layout.addWidget(entry_widget)

    def __handle_move_output_up_callback(self, output: Output):
        result = QMessageBox.question(self, "Are you sure?", "This will remove an entry from your Output and possibly add it to any subsequent Outputs. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        self._engine.move_output_target_up_by_id(output.unique_id)
        self._parent.handle_update()

    def __handle_move_output_down_callback(self, output: Output):
        result = QMessageBox.question(self, "Are you sure?", "This will possibly remove an entry from any subsequent Output and add it to this Output. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        self._engine.move_output_target_down_by_id(output.unique_id)
        self._parent.handle_update()

    def __handle_move_up_callback(self, entry_id: str, state: bool):
        output_id = self.__output_selector.currentData()
        output = self._engine.get_output_by_id(output_id)
        if state:
            target_list = output.members
        else:
            target_list = output.ignored
        current_index = target_list.index(entry_id)
        target_list.insert(current_index - 1, target_list.pop(current_index))
        self._engine.edit_output(output)
        self.handle_update()

    def __handle_move_down_callback(self, entry_id: str, state: bool):
        output_id = self.__output_selector.currentData()
        output = self._engine.get_output_by_id(output_id)
        if state:
            target_list = output.members
        else:
            target_list = output.ignored
        current_index = target_list.index(entry_id)
        target_list.insert(current_index + 1, target_list.pop(current_index))
        self._engine.edit_output(output)
        self.handle_update()

    def __handle_entry_changed_state_callback(self, entry_id: str, state: bool):
        output_id = self.__output_selector.currentData()
        output = self._engine.get_output_by_id(output_id)
        if state:
            source = output.members
            target = output.ignored
        else:
            source = output.ignored
            target = output.members
        source.remove(entry_id)
        target.append(entry_id)
        self._engine.edit_output(output)
        self.handle_update()


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


def add_or_edit_output(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', original_output: Output | None):
    # If we weren't provided an output, create a dummy and have the engine 'register it' for now
    # This dummy will need to be cleaned up properly in the advent of a failure.
    if original_output is None:
        entry_id = engine.get_most_recent_entry_id()
        output = Output("MOCK", "MOCK", entry_id, list(), list())

    # Make a copy so we don't inline edit our original
    else:
        output = Output(original_output.name, original_output.gsheet_target, original_output.target_entry_id, original_output.members, original_output.ignored)

    # Build a dialog to edit the current category information
    output_dialog = OutputDialog(engine, output)
    output_dialog.exec()

    # Validate dialog output
    if not output_dialog.success:
        return

    # Check no mock
    if output_dialog.output.name == "MOCK" or output_dialog.output.gsheet_target == "MOCK":
        return

    # Add our new category
    if original_output is None:
        engine.add_output_to_head(output_dialog.output)

    # Edit the category in our engine
    else:
        original_output.name = output_dialog.output.name
        original_output.gsheet_target = output_dialog.output.gsheet_target
        original_output.members = output_dialog.output.members
        original_output.ignored = output_dialog.output.ignored

    # Trigger a refresh of the UI
    parent.handle_update()


def delete_output(engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', output: Output):
    result = QMessageBox.question(parent, "Are you sure?", "Are you sure you want to delete this output?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if result != QMessageBox.StandardButton.Yes:
        return

    engine.delete_output(output)
    parent.handle_update()
