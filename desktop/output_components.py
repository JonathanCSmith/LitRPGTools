from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QComboBox, QPushButton, QWidget, QVBoxLayout, QScrollArea, QFormLayout, QCheckBox, QHBoxLayout, QMessageBox, QLabel, QFrame, QLineEdit, QListWidget, QAbstractItemView, QListWidgetItem

from data.models import Output
from desktop import entry_components
from desktop.custom_generic_components import VisibleDynamicSplitPanel, Content

if TYPE_CHECKING:
    from desktop.guis import DesktopGUI


class OutputsTab(VisibleDynamicSplitPanel, Content):
    def __init__(self, root_gui: 'DesktopGUI'):
        super().__init__()
        self.root_gui = root_gui

        # Currently selected
        self.selected_output_id = None

        # Main components
        self.__sidebar_widget = QWidget()
        self.__setup_sidebar()

        self.__entry_view = QScrollArea()
        self.__setup_entry_view()

        # Core display
        self.addWidget(self.__sidebar_widget)
        self.addWidget(self.__entry_view)
        self.setStretchFactor(0, 20)
        self.setStretchFactor(1, 200)
        self.setSizes([200, 1000])
        self.setContentsMargins(0, 0, 0, 0)

    def __setup_sidebar(self):
        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # Output selector
        self.__output_selector = QComboBox()
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
        self.__sidebar_widget.setLayout(self.__layout)
        self.__sidebar_widget.setContentsMargins(0, 0, 0, 0)

    def __setup_entry_view(self):
        self.selected_entry_id = None

        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view.setLayout(self.__results_view_layout)
        self.__entry_view.setWidget(self.__results_view)
        self.__entry_view.setWidgetResizable(True)
        self.__entry_view.setContentsMargins(0, 0, 0, 0)

    def fill_content(self):
        self.clear_content()

        self.__fill_output_selector()
        self.__fill_active_list()
        self.__fill_entry_view()

    def __fill_output_selector(self):
        self.__output_selector.blockSignals(True)
        current_text = self.__output_selector.currentText()
        self.__output_selector.clear()

        # Add all the outputs
        outputs = self.root_gui.runtime.data_manager.get_outputs()
        for index, output in enumerate(outputs):
            self.__output_selector.addItem(output.name)
            self.__output_selector.setItemData(index, output.unique_id)

        # Restore old selected where relevant
        if current_text is not None:
            self.__output_selector.setCurrentText(current_text)
        self.__output_selector.blockSignals(False)

    def __fill_active_list(self):
        currently_selected = self.__active_list.currentRow()
        current_history_entry = self.root_gui.runtime.data_manager.get_entry_id_by_history_index(self.root_gui.runtime.data_manager.get_current_history_index())
        current_entry_selected = None
        if currently_selected != -1:
            current_entry_selected = self.__active_list.item(currently_selected).data(Qt.ItemDataRole.UserRole)

        # Get current output
        output_id = self.__output_selector.currentData()
        if output_id is None:
            self.selected_output_id = None
            return
        self.selected_output_id = output_id
        output = self.root_gui.runtime.data_manager.get_output_by_id(self.selected_output_id)

        # Block signals and clear list
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Add to our list
        for index, entry_id in enumerate(output.members):
            display_string = self.root_gui.create_entry_summary_string(entry_id, output_index=index)
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)

            # If the item is the current history head
            if entry_id == current_history_entry:
                colour = Qt.GlobalColor.blue
            elif current_entry_selected in self.root_gui.runtime.data_manager.get_entry_revisions_for_id(entry_id):
                colour = Qt.GlobalColor.yellow
            else:
                colour = Qt.GlobalColor.green
            item.setForeground(colour)

            self.__active_list.addItem(item)

        for entry_id in output.ignored:
            display_string = self.root_gui.create_entry_summary_string(entry_id, output_index="-")
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)

            # If the item is the current history head
            if entry_id == current_history_entry:
                colour = Qt.GlobalColor.blue
            elif current_entry_selected in self.root_gui.runtime.data_manager.get_entry_revisions_for_id(entry_id):
                colour = Qt.GlobalColor.yellow
            else:
                colour = Qt.GlobalColor.red
            item.setForeground(colour)

            self.__active_list.addItem(item)

        # Return signals
        self.__active_list.setCurrentRow(currently_selected)
        self.__active_list.blockSignals(False)

    def __fill_entry_view(self):
        # Clear our current data
        result = self.__results_view_layout.itemAt(0)
        if result is not None:
            result_widget = result.widget()
            result_widget.deleteLater()

        # Obtain the currently selected output and bail if there's nothing
        if self.selected_output_id is None:
            return

        # Obtain the currently selected item and bail if there's nothing
        currently_selected = self.__active_list.currentItem()
        if currently_selected is None:
            self.selected_entry_id = None
            return

        # Store the current selection
        self.selected_entry_id = currently_selected.data(Qt.ItemDataRole.UserRole)

        self.__fill_output_controls()

        # Gather required data
        entry = self.root_gui.runtime.data_manager.get_entry_by_id(self.selected_entry_id)
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

        # Fill our entry
        entry_form = QWidget()
        entry_form_layout = QFormLayout()
        entry_components.create_entry_form(
            self.root_gui,
            entry_form_layout,
            character,
            category,
            entry,
            current_index,
            readonly=True,
            translate_with_dynamic_data=should_display_dynamic_data,
            dynamic_data_index=target_index)
        entry_form.setLayout(entry_form_layout)

        # Props for this entry type in output
        members_length = len(self.selected_output_id.members)
        ignored_length = len(self.selected_output_id.ignored)
        max_size = members_length + ignored_length

        # Entry Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        edit_entry_button = QPushButton("Edit Entry")
        edit_entry_button.clicked.connect(self.__handle_edit_entry_callback)
        entry_controls_layout.addWidget(edit_entry_button)
        move_up_button = QPushButton("Move Entry Up")
        if current_index > 0:
            move_up_button.clicked.connect(self.__handle_move_entry_up_callback)
        entry_controls_layout.addWidget(move_up_button)
        move_down_button = QPushButton("Move Entry Down")
        if current_index < max_size:
            move_down_button.clicked.connect(self.__handle_move_entry_down_callback)
        entry_controls_layout.addWidget(move_down_button)
        enabled_checkbox = QCheckBox("Entry In Output?")
        enabled_checkbox.setChecked(self.selected_entry_id in self.selected_output_id.members)
        enabled_checkbox.clicked.connect(self.__handle_entry_changed_state_callback)
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

    def __fill_output_controls(self):
        # Controls
        output_controls = QWidget()
        output_controls_layout = QHBoxLayout()
        output_up_button = QPushButton("Move Output End UP")
        output_up_button.clicked.connect(self.__handle_move_output_end_up_callback)
        output_controls_layout.addWidget(output_up_button)
        output_down_button = QPushButton("Move Output End DOWN")
        output_down_button.clicked.connect(self.__handle_move_output_end_down_callback)
        output_controls_layout.addWidget(output_down_button)
        output_edit_button = QPushButton("Edit Output")
        output_edit_button.clicked.connect(self.__handle_edit_output_callback)
        output_controls_layout.addWidget(output_edit_button)
        output_delete_button = QPushButton("Delete Output")
        output_delete_button.clicked.connect(self.__handle_delete_output_callback)
        output_controls_layout.addWidget(output_delete_button)
        output_controls.setLayout(output_controls_layout)

        # Basic props
        basic_props_widget = QWidget()
        basic_props_layout = QFormLayout()
        basic_props_layout.addRow("Output Name:", QLabel(self.selected_output_id.name))
        basic_props_layout.addRow("Output Target Gsheet:", QLabel(self.selected_output_id.gsheet_target))
        basic_props_layout.addRow("", output_controls)
        basic_props_widget.setLayout(basic_props_layout)
        self.__results_view_layout.addWidget(basic_props_widget)

        # Spacer
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        separator.setLineWidth(3)
        separator.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout.addWidget(separator)

    def clear_content(self):
        self.blockSignals(True)
        self.__active_list.clear()
        self.selected_output_id = None
        self.selected_entry_id = None
        self.__fill_entry_view()  # Should clear based on us having no item selected
        self.blockSignals(False)

    def __handle_output_selector_changed_callback(self):
        self.__fill_active_list()
        self.__fill_entry_view()

    def __handle_sidebar_selection_changed_callback(self):
        self.__repaint_list()
        self.__fill_entry_view()

    def __repaint_list(self):
        self.__active_list.blockSignals(True)
        current_index_selected = self.__active_list.currentRow()
        current_entry_selected = self.__active_list.item(current_index_selected).data(Qt.ItemDataRole.UserRole)
        current_history_entry = self.root_gui.runtime.data_manager.get_entry_id_by_history_index(self.root_gui.runtime.data_manager.get_current_history_index())

        output = self.root_gui.runtime.data_manager.get_output_by_id(self.selected_output_id)
        for i in range(self.__active_list.count()):
            entry_id = self.__active_list.item(i).data(Qt.ItemDataRole.UserRole)

            # If the item is the current history head
            if entry_id == current_history_entry:
                colour = Qt.GlobalColor.blue
            elif current_entry_selected in self.root_gui.runtime.data_manager.get_entry_revisions_for_id(entry_id):
                colour = Qt.GlobalColor.yellow
            elif entry_id in output.members:
                colour = Qt.GlobalColor.green
            else:
                colour = Qt.GlobalColor.red

            self.__active_list.item(i).setForeground(colour)
        self.__active_list.blockSignals(False)

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

    def __handle_move_output_end_up_callback(self):
        result = QMessageBox.question(self, "Are you sure?", "This will remove an entry your output and add it the next output if possible. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        self.root_gui.runtime.data_manager.move_output_target_up_by_id(self.selected_output_id)
        self.__handle_data_changed()
        self.__fill_entry_view()

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

    def __handle_move_output_end_down_callback(self):
        result = QMessageBox.question(self, "Are you sure?", "This will possibly remove an entry from a subsequent output if possible and add it to your own. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if result != QMessageBox.StandardButton.Yes:
            return

        self.root_gui.runtime.data_manager.move_output_target_down_by_id(self.selected_output_id)
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_edit_output_callback(self):
        add_or_edit_output(self.root_gui, self.selected_output_id)
        self.fill_content()

    def __handle_delete_output_callback(self):
        delete_output(self.root_gui, self.selected_output_id)
        self.fill_content()

    def __handle_edit_entry_callback(self):
        entry_components.edit_entry(self.root_gui, self, self.selected_entry_id)
        self.root_gui.runtime.data_manager.move_output_target_down_by_id(self.selected_output_id)
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_move_entry_up_callback(self):
        output = self.root_gui.runtime.data_manager.get_output_by_id(self.selected_output_id)
        try:
            current_index = output.members.index(self.selected_entry_id)
            output.members.insert(current_index - 1, output.members.pop(current_index))
        except ValueError:
            current_index = output.ignored.index(self.selected_entry_id)
            output.ignored.insert(current_index - 1, output.ignored.pop(current_index))

        self.root_gui.runtime.data_manager.edit_output(output)
        self.root_gui.runtime.data_manager.move_output_target_down_by_id(self.selected_output_id)
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_move_entry_down_callback(self):
        output = self.root_gui.runtime.data_manager.get_output_by_id(self.selected_output_id)
        try:
            current_index = output.members.index(self.selected_entry_id)
            output.members.insert(current_index + 1, output.members.pop(current_index))
        except ValueError:
            current_index = output.ignored.index(self.selected_entry_id)
            output.ignored.insert(current_index + 1, output.ignored.pop(current_index))

        self.root_gui.runtime.data_manager.edit_output(output)
        self.root_gui.runtime.data_manager.move_output_target_down_by_id(self.selected_output_id)
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_entry_changed_state_callback(self):
        output = self.root_gui.runtime.data_manager.get_output_by_id(self.selected_output_id)
        if self.selected_entry_id in output.members:
            source = output.members
            target = output.ignored
        else:
            source = output.ignored
            target = output.members
        source.remove(self.selected_entry_id)
        target.append(self.selected_entry_id)

        self.root_gui.runtime.data_manager.edit_output(output)
        self.root_gui.runtime.data_manager.move_output_target_down_by_id(self.selected_output_id)
        self.__handle_data_changed()
        self.__fill_entry_view()


class OutputDialog(QDialog):
    def __init__(self, gui: 'DesktopGUI', output: Output):
        super(OutputDialog, self).__init__()
        self.gui = gui
        self.output = output
        self.success = False

        # General
        self.setWindowTitle("Output.")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)

        # Form components
        self.__name_field = QLineEdit()
        self.__target_gsheet = QComboBox()
        self.__target_gsheet.addItems(self.gui.runtime.data_manager.get_unassigned_gsheets())
        self.__cancel_button = QPushButton("Cancel")
        self.__cancel_button.clicked.connect(self.__handle_cancel_callback)
        self.__done_button = QPushButton("Done")
        self.__done_button.clicked.connect(self.__handle_done_callback)

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

    def __handle_cancel_callback(self):
        self.success = False
        self.close()

    def __handle_done_callback(self):
        outputs = self.gui.runtime.data_manager.get_outputs()
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
    def __init__(self, gui: 'DesktopGUI'):
        super().__init__(parent=gui)
        self.parent_gui = gui
        self.success = False
        self.view_id = None

        # Character selector
        self.__view_selector = QComboBox()
        self.__view_selector.addItem("Please Select A View")

        # Fill in our character data
        for index, view in enumerate(self.parent_gui.runtime.data_manager.get_outputs()):
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


def add_or_edit_output(gui: 'DesktopGUI', original_output: Output | None):
    # Validate gsheets environment
    if gui.runtime.data_manager.get_unassigned_gsheets() is None:
        QMessageBox.question(
            gui,
            "Invalid GSheets Environment",
            "There are either no gsheets available or your gsheets credentials have not been set up.",
            QMessageBox.StandardButton.Ok, QMessageBox.StandardButton.Ok
        )
        return

    # If we weren't provided an output, create a dummy and have the engine 'register it' for now
    # This dummy will need to be cleaned up properly in the advent of a failure.
    if original_output is None:
        entry_id = gui.runtime.data_manager.get_most_recent_entry_id()
        output = Output("MOCK", "MOCK", entry_id, list(), list())

    # Make a copy so we don't inline edit our original
    else:
        output = Output(original_output.name, original_output.gsheet_target, original_output.target_entry_id, original_output.members, original_output.ignored)

    # Build a dialog to edit the current category information
    output_dialog = OutputDialog(gui, output)
    output_dialog.exec()

    # Validate dialog output
    if not output_dialog.success:
        return

    # Check no mock
    if output_dialog.output.name == "MOCK" or output_dialog.output.gsheet_target == "MOCK":
        return

    # Add our new output
    if original_output is None:
        gui.runtime.data_manager.add_output_to_head(output_dialog.output)
        original_output = output_dialog.output

    # Edit the category in our engine
    else:
        original_output.name = output_dialog.output.name
        original_output.gsheet_target = output_dialog.output.gsheet_target
        original_output.members = output_dialog.output.members
        original_output.ignored = output_dialog.output.ignored

    # Trigger a refresh of the UI
    return original_output


def delete_output(gui: 'DesktopGUI', output: Output):
    result = QMessageBox.question(gui, "Are you sure?", "Are you sure you want to delete this output?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if result != QMessageBox.StandardButton.Yes:
        return

    gui.runtime.data_manager.delete_output(output)
