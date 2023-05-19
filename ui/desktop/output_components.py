from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QComboBox, QPushButton, QWidget, QVBoxLayout, QScrollArea, QFormLayout, QCheckBox, QHBoxLayout, QMessageBox, QLabel, QFrame, QLineEdit, QListWidget, QAbstractItemView, QListWidgetItem

from data import Output, Entry, Character, Category
from ui.desktop import entry_components
from ui.desktop.custom_generic_components import VisibleDynamicSplitPanel

if TYPE_CHECKING:
    from main import LitRPGToolsEngine
    from ui.desktop.gui import LitRPGToolsDesktopGUI


class OutputsTab(VisibleDynamicSplitPanel):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Currently selected
        self.output = None
        self.results = list()

        # Main components
        self._sidebar_widget = OutputSidebar(self, engine)
        self._view_widget = OutputView(self, engine)

        # Core display
        self.addWidget(self._sidebar_widget)
        self.addWidget(self._view_widget)
        self.setStretchFactor(0, 20)
        self.setStretchFactor(1, 200)
        self.setSizes([200, 1000])
        self.setContentsMargins(0, 0, 0, 0)

    def draw(self):
        self._sidebar_widget.draw()
        self._view_widget.draw()

    def get_current_selection(self):
        return self._sidebar_widget.get_currently_selected()

    def set_curently_selected(self, index):
        self._sidebar_widget.set_currently_selected(index)

    def get_should_display_dynamic_absolute(self):
        return self._sidebar_widget.view_dynamic_absolute

    def get_should_display_dynamic_relative(self):
        return self._sidebar_widget.view_dynamic_relative

    def _selection_changed(self):
        self._view_widget.draw()


class OutputSidebar(QWidget):
    def __init__(self, parent: OutputsTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # Output selector
        self.__output_selector = QComboBox()
        self.__fill_output_selector()
        self.__output_selector.currentTextChanged.connect(self.__handle_output_selector_changed_callback)

        # View dynamic
        self.__view_dynamic_data_relative_checkbox = QCheckBox("View Dynamic Data (Respect Current History Index)")
        self.__view_dynamic_data_relative_checkbox.clicked.connect(self.__handle_view_dynamic_data_relative_callback)
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        self.__view_dynamic_data_absolute_checkbox = QCheckBox("View Dynamic Data (Respect Entry Index)")
        self.__view_dynamic_data_absolute_checkbox.clicked.connect(self.__handle_view_dynamic_data_absolute_callback)
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__active_list)
        self.__layout.addWidget(self.__output_selector)
        self.__layout.addWidget(self.__view_dynamic_data_relative_checkbox)
        self.__layout.addWidget(self.__view_dynamic_data_absolute_checkbox)
        self.setLayout(self.__layout)
        self.setContentsMargins(0, 0, 0, 0)

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
        self._parent.draw()

    def __handle_sidebar_selection_changed_callback(self):
        self.__paint_list()
        self._parent._selection_changed()

    def __paint_list(self):
        for i in range(self.__active_list.count()):
            colour = self.__get_list_row_colour_from_context(i)
            self.__active_list.item(i).setForeground(colour)

    def __get_list_row_colour_from_context(self, entry_index) -> Qt.GlobalColor:
        # First check if it's our active 'head'
        if self._engine.get_current_history_index() == entry_index:
            return Qt.GlobalColor.blue

        output = self._parent.output
        members_length = len(output.members)
        ignored_length = len(output.ignored)
        if entry_index <= members_length - 1:
            entry_id = output.members[entry_index]
        else:
            entry_id = output.ignored[entry_index - members_length]

        # Check for a familial relationship with the currently selected
        familial_relatives = self._engine.get_entry_revisions_for_id(entry_id)
        if self.__active_list.item(entry_index).data(Qt.ItemDataRole.UserRole) in familial_relatives:
            return Qt.GlobalColor.yellow

        # Highlight based on 'selector' to green?
        output = self._parent.output
        if entry_id in output.members:
            return Qt.GlobalColor.green
        elif entry_id in output.ignored:
            return Qt.GlobalColor.red

        return Qt.GlobalColor.white  # Shouldn't happen?

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
        currently_selected = self.__active_list.currentRow()
        if currently_selected == -1:
            currently_selected = 0

        # Fill our
        self.__fill_output_selector()

        # Get current output
        output_id = self.__output_selector.currentData()
        if output_id is None:
            return
        output = self._engine.get_output_by_id(output_id)
        if output is None:
            return

        # Set our result
        self._parent.output = output

        # Block signals and clear list
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Add to our list
        whole_index = 0
        for entry_id in output.members:
            entry = self._engine.get_entry_by_id(entry_id)
            category = self._engine.get_category_by_id(entry.category_id)
            character = self._engine.get_character_by_id(entry.character_id)

            # Display string format
            if entry.parent_id is None:
                display_string = category.creation_text
            else:
                display_string = category.update_text
            display_string = self.__fill_entry_display_string(display_string, whole_index, character, category, entry)

            # Add the string
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, whole_index)
            self.__active_list.addItem(item)
            whole_index += 1

        for entry_id in output.ignored:
            entry = self._engine.get_entry_by_id(entry_id)
            category = self._engine.get_category_by_id(entry.category_id)
            character = self._engine.get_character_by_id(entry.character_id)

            # Display string format
            if entry.parent_id is None:
                display_string = category.creation_text
            else:
                display_string = category.update_text
            display_string = self.__fill_entry_display_string(display_string, whole_index, character, category, entry)

            # Add the string
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, whole_index)
            self.__active_list.addItem(item)
            whole_index += 1

        # Return signals
        self.__active_list.blockSignals(False)
        self.__active_list.setCurrentRow(currently_selected)

    def __fill_entry_display_string(self, template_string: str, index: int, character: Character, category: Category, entry: Entry):
        string_result = template_string.format(*entry.data)  # TODO! Codify some nice stuff here
        return "[" + str(index) + "] (" + character.name + "): " + string_result

    def get_currently_selected(self):
        return self.__active_list.currentItem()

    def set_currently_selected(self, index):
        self.__active_list.setCurrentRow(index)


class OutputView(QScrollArea):
    def __init__(self, parent: OutputsTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Results
        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view.setLayout(self.__results_view_layout)
        self.setWidget(self.__results_view)
        self.setWidgetResizable(True)
        self.setContentsMargins(0, 0, 0, 0)

    def draw(self):
        # Clear out our current data
        for i in reversed(range(0, self.__results_view_layout.count())):
            item = self.__results_view_layout.takeAt(i)
            if item is not None:
                try:
                    item.widget().deleteLater()
                except AttributeError as e:
                    continue

        # Get current output and draw
        output = self._parent.output
        if output is None:
            return
        self.__draw_output(output)

    def __draw_output(self, output: Output):
        # Controls
        output_controls = QWidget()
        output_controls_layout = QHBoxLayout()
        output_up_button = QPushButton("Move Output End UP")
        output_up_button.clicked.connect(partial(self.__handle_move_output_end_up_callback, output))
        output_controls_layout.addWidget(output_up_button)
        output_down_button = QPushButton("Move Output End DOWN")
        output_down_button.clicked.connect(partial(self.__handle_move_output_end_down_callback, output))
        output_controls_layout.addWidget(output_down_button)
        output_edit_button = QPushButton("Edit Output")
        output_edit_button.clicked.connect(partial(self.__handle_edit_output_callback, output))
        output_controls_layout.addWidget(output_edit_button)
        output_delete_button = QPushButton("Delete Output")
        output_delete_button.clicked.connect(partial(self.__handle_delete_output_callback, output))
        output_controls_layout.addWidget(output_delete_button)
        output_controls.setLayout(output_controls_layout)

        # Basic props
        basic_props_widget = QWidget()
        basic_props_layout = QFormLayout()
        basic_props_layout.addRow("Output Name:", QLabel(output.name))
        basic_props_layout.addRow("Output Target Gsheet:", QLabel(output.gsheet_target))
        basic_props_layout.addRow("", output_controls)
        basic_props_widget.setLayout(basic_props_layout)
        self.__results_view_layout.addWidget(basic_props_widget)

        # Spacer
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        separator.setLineWidth(3)
        separator.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout.addWidget(separator)

        # Render the currently selected entry
        currently_selected = self._parent.get_current_selection()
        if currently_selected is not None:
            entry_index = currently_selected.data(Qt.ItemDataRole.UserRole)
            members_length = len(output.members)
            ignored_length = len(output.ignored)
            max_size = members_length + ignored_length
            if entry_index <= members_length - 1:
                entry_id = output.members[entry_index]
                entry = self._engine.get_entry_by_id(entry_id)
                self.__draw_entry(max_size, entry_index, entry, True)
            else:
                entry_id = output.ignored[entry_index - members_length]
                entry = self._engine.get_entry_by_id(entry_id)
                self.__draw_entry(max_size, entry_index, entry, False)

    def __draw_entry(self, max_index: int, current_index: int, entry: Entry, state: bool):
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
        entry_components.create_entry_form(self._engine, entry_form_layout, character, category, entry, current_index, readonly=True, translate_with_dynamic_data=should_display_dynamic_data, dynamic_data_index=target_index)
        entry_form.setLayout(entry_form_layout)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        edit_entry_button = QPushButton("Edit Entry")
        edit_entry_button.clicked.connect(partial(self.__handle_edit_entry_callback, entry))
        entry_controls_layout.addWidget(edit_entry_button)
        move_up_button = QPushButton("Move Entry Up")
        if current_index > 0:
            move_up_button.clicked.connect(partial(self.__handle_move_entry_up_callback, entry.unique_id, state))
        entry_controls_layout.addWidget(move_up_button)
        move_down_button = QPushButton("Move Entry Down")
        if current_index < max_index:
            move_down_button.clicked.connect(partial(self.__handle_move_entry_down_callback, entry.unique_id, state))
        entry_controls_layout.addWidget(move_down_button)
        enabled_checkbox = QCheckBox("Entry In Output?")
        enabled_checkbox.setChecked(state)
        enabled_checkbox.clicked.connect(partial(self.__handle_entry_changed_state_callback, entry.unique_id, state))
        entry_controls_layout.addWidget(enabled_checkbox)
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

    def __handle_move_output_end_up_callback(self, output: Output):
        result = QMessageBox.question(self, "Are you sure?", "This will remove an entry from your Output and possibly add it to any subsequent Outputs. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        self._engine.move_output_target_up_by_id(output.unique_id)
        self._parent.draw()

    def __handle_move_output_end_down_callback(self, output: Output):
        result = QMessageBox.question(self, "Are you sure?", "This will possibly remove an entry from any subsequent Output and add it to this Output. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        self._engine.move_output_target_down_by_id(output.unique_id)
        self._parent.draw()

    def __handle_edit_output_callback(self, output: Output):
        add_or_edit_output(self._engine, output)
        self._parent.draw()

    def __handle_delete_output_callback(self, output: Output):
        delete_output(self._engine, self, output)
        self._parent.draw()

    def __handle_edit_entry_callback(self, entry: Entry):
        entry_components.edit_entry(self._engine, self, entry)
        self._parent.draw()

    def __handle_move_entry_up_callback(self, entry_id: str, state: bool):
        output = self._parent.output
        if state:
            target_list = output.members
        else:
            target_list = output.ignored
        current_index = target_list.index(entry_id)
        target_list.insert(current_index - 1, target_list.pop(current_index))
        self._engine.edit_output(output)
        self._parent.draw()
        self._parent.set_curently_selected(current_index - 1)

    def __handle_move_entry_down_callback(self, entry_id: str, state: bool):
        output = self._parent.output
        if state:
            target_list = output.members
        else:
            target_list = output.ignored
        current_index = target_list.index(entry_id)
        target_list.insert(current_index + 1, target_list.pop(current_index))
        self._engine.edit_output(output)
        self._parent.draw()
        self._parent.set_curently_selected(current_index + 1)

    def __handle_entry_changed_state_callback(self, entry_id: str, state: bool):
        output = self._parent.output
        if state:
            source = output.members
            target = output.ignored
        else:
            source = output.ignored
            target = output.members
        source.remove(entry_id)
        target.append(entry_id)
        self._engine.edit_output(output)
        self._parent.draw()


class OutputDialog(QDialog):
    def __init__(self, engine: 'LitRPGToolsEngine', output: Output):
        super(OutputDialog, self).__init__()
        self.__engine = engine
        self.output = output
        self.success = False

        # General
        self.setWindowTitle("Output.")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        # Form components
        self.__name_field = QLineEdit()
        self.__target_gsheet = QComboBox()
        self.__target_gsheet.addItems(self.__engine.get_unassigned_gsheets())
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

        # Results view
        # self.__results_view = QWidget()
        # self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        # self.__results_view_layout = QVBoxLayout()
        # self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        # self.__results_view.setLayout(self.__results_view_layout)
        # self.__results_view_scroll = QScrollArea()
        # self.__results_view_scroll.setWidget(self.__results_view)
        # self.__results_view_scroll.setWidgetResizable(True)

        # Form
        self.__layout = QFormLayout()
        self.__layout.addRow("Unique Name:", self.__name_field)
        self.__layout.addRow("Target GSheet:", self.__target_gsheet)
        # self.__layout.addRow("Applicable Entries:", self.__results_view_scroll)
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
        # self.__draw_results()

    # def __draw_results(self):
    #     # Clear our current results
    #     for i in reversed(range(self.__results_view_layout.count())):
    #         w = self.__results_view_layout.itemAt(i).widget()
    #         self.__results_view_layout.removeWidget(w)
    #         w.deleteLater()
    #
    #     # Render the entries that are actually included in our output first
    #     max_index = len(self.output.members)
    #     for current_index, result_id in enumerate(self.output.members):
    #         result = self.__engine.get_entry_by_id(result_id)
    #         self.__draw_entry(max_index, current_index, result, True)
    #
    #     # Render the entries that are not in our output
    #     max_index = len(self.output.ignored)
    #     for current_index, result_id in enumerate(self.output.ignored):
    #         result = self.__engine.get_entry_by_id(result_id)
    #         self.__draw_entry(max_index, current_index, result, False)
    #
    # def __draw_entry(self, max_index: int, current_index: int, entry: Entry, state: bool):
    #     character = self.__engine.get_character_by_id(entry.character_id)
    #     category = self.__engine.get_category_by_id(entry.category_id)
    #     entry_index = self.__engine.get_entry_index_in_history(entry.unique_id)
    #
    #     # Form
    #     entry_form = QWidget()
    #     entry_form_layout = QFormLayout()
    #     entry_components.create_entry_form(entry_form_layout, character, category, entry, entry_index)
    #     entry_form.setLayout(entry_form_layout)
    #
    #     # Controls
    #     entry_controls = QWidget()
    #     entry_controls_layout = QVBoxLayout()
    #     move_up_button = QPushButton("Move Entry Up")
    #     if current_index > 0:
    #         move_up_button.clicked.connect(self.__handle_move_up_callback, current_index, state)
    #     entry_controls_layout.addWidget(move_up_button)
    #     move_down_button = QPushButton("Move Entry Down")
    #     if current_index < max_index - 1:
    #         move_down_button.clicked.connect(self.__handle_move_down_callback, current_index, state)
    #     entry_controls_layout.addWidget(move_down_button)
    #     enabled_checkbox = QCheckBox("Entry In Output?")
    #     enabled_checkbox.setChecked(state)
    #     enabled_checkbox.clicked.connect(self.__handle_entry_changed_state_callback, current_index, entry.unique_id, state)
    #     entry_controls_layout.addWidget(enabled_checkbox)
    #     spacer = QWidget()
    #     entry_controls_layout.addWidget(spacer)
    #     entry_controls_layout.setStretchFactor(spacer, 100)
    #     entry_controls_layout.setContentsMargins(0, 0, 0, 0)
    #     entry_controls.setLayout(entry_controls_layout)
    #
    #     # Main container
    #     entry_widget = QWidget()
    #     entry_widget_layout = QHBoxLayout()
    #     entry_widget_layout.addWidget(entry_form)
    #     entry_widget_layout.setStretchFactor(entry_form, 90)
    #     entry_widget_layout.addWidget(entry_controls)
    #     entry_widget_layout.setStretchFactor(entry_controls, 10)
    #     entry_widget_layout.setContentsMargins(0, 0, 0, 0)
    #     entry_widget.setObjectName("bordered")
    #     entry_widget.setLayout(entry_widget_layout)
    #     self.__results_view_layout.addWidget(entry_widget)
    #
    # def __handle_move_up_callback(self, current_index: int, state: bool):
    #     if state:
    #         target_list = self.output.members
    #     else:
    #         target_list = self.output.ignored
    #     target_list.insert(current_index - 1, target_list.pop(current_index))
    #
    # def __handle_move_down_callback(self, current_index: int, state: bool):
    #     if state:
    #         target_list = self.output.members
    #     else:
    #         target_list = self.output.ignored
    #     target_list.insert(current_index + 1, target_list.pop(current_index))
    #
    # def __handle_entry_changed_state_callback(self, current_index: int, state: bool):
    #     if state:
    #         source = self.output.members
    #         target = self.output.ignored
    #     else:
    #         source = self.output.ignored
    #         target = self.output.members
    #     entry_id = source.pop(current_index)
    #     target.append(entry_id)

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

        # Bail if there is no text in the gsheet target
        target = self.__target_gsheet.currentText()
        if target is None or target == "":
            self.success = False
            self.close()
            return

        # Assign to our mock output
        self.output.name = name
        self.output.gsheet_target = self.__target_gsheet.currentText()

        # Exit cleanly
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


def add_or_edit_output(engine: 'LitRPGToolsEngine', called: QWidget, original_output: Output | None):
    # Validate gsheets environment
    if engine.get_unassigned_gsheets() is None:
        QMessageBox.question(
            called,
            "Invalid GSheets Environment",
            "There are either no gsheets available or your gsheets credentials have not been set up.",
            QMessageBox.StandardButton.Ok , QMessageBox.StandardButton.Ok
        )
        return

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
        original_output = output_dialog.output

    # Edit the category in our engine
    else:
        original_output.name = output_dialog.output.name
        original_output.gsheet_target = output_dialog.output.gsheet_target
        original_output.members = output_dialog.output.members
        original_output.ignored = output_dialog.output.ignored

    # Trigger a refresh of the UI
    return original_output


def delete_output(engine: 'LitRPGToolsEngine', caller: QWidget, output: Output):
    result = QMessageBox.question(caller, "Are you sure?", "Are you sure you want to delete this output?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if result != QMessageBox.StandardButton.Yes:
        return

    engine.delete_output(output)
