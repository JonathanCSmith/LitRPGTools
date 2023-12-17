from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QAction
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout, QLineEdit, QFrame, QListWidgetItem, QListWidget, QAbstractItemView, QCheckBox, QComboBox, QMenu

from desktop import output_components, entry_components
from desktop.custom_generic_components import VisibleDynamicSplitPanel, ShadedWidget, Content

if TYPE_CHECKING:
    from desktop.guis import DesktopGUI


class HistoryTab(VisibleDynamicSplitPanel, Content):
    def __init__(self, root_gui: 'DesktopGUI'):
        super().__init__()
        self.root_gui = root_gui

        # Sidebar
        self.__sidebar_widget = QWidget()
        self.__setup_sidebar()

        # Selected view
        self.__entry_view = QWidget()
        self.__setup_entry_view()

        # Core display
        self.addWidget(self.__sidebar_widget)
        self.addWidget(self.__entry_view)
        self.setStretchFactor(0, 20)
        self.setStretchFactor(1, 200)
        self.setSizes([200, 1000])
        self.setContentsMargins(0, 0, 0, 0)

    def __setup_sidebar(self):
        # Allow Selection of what character we want to display in the sidebar
        self.__character_filter = QComboBox()
        self.__character_filter.currentTextChanged.connect(self.__handle_filter_changed_callback)

        # Allow Selection of what category we want to display in the sidebar
        self.__category_filter = QComboBox()
        self.__category_filter.currentTextChanged.connect(self.__handle_filter_changed_callback)

        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # New entry button
        self.__new_entry_button = QPushButton("New Entry at Current History Index")
        self.__new_entry_button.clicked.connect(self.__handle_new_entry_callback)

        # New output button
        self.__new_view_button = QPushButton("New Output at Current History Index")
        self.__new_view_button.clicked.connect(self.__handle_new_output_callback)

        # Dynamic data buttons
        self.__view_dynamic_data_relative_checkbox = QCheckBox("View Dynamic Data (Respect Current History Index)")
        self.__view_dynamic_data_relative_checkbox.clicked.connect(self.__handle_view_dynamic_data_relative_callback)
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        self.__view_dynamic_data_absolute_checkbox = QCheckBox("View Dynamic Data (Respect Entry Index)")
        self.__view_dynamic_data_absolute_checkbox.clicked.connect(self.__handle_view_dynamic_data_absolute_callback)
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__character_filter)
        self.__layout.addWidget(self.__category_filter)
        self.__layout.addWidget(self.__active_list)
        self.__layout.addWidget(self.__new_entry_button)
        self.__layout.addWidget(self.__new_view_button)
        self.__layout.addWidget(self.__view_dynamic_data_relative_checkbox)
        self.__layout.addWidget(self.__view_dynamic_data_absolute_checkbox)
        self.__sidebar_widget.setLayout(self.__layout)
        self.__sidebar_widget.setContentsMargins(0, 0, 0, 0)

    def __setup_entry_view(self):
        # Currently selected
        self.selected_entry_id = None

        # Alt pane palette
        self.__alternate_palette = QPalette()
        self.__alternate_palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        self.__alternate_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        self.__alternate_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))

        # Ancestor Pane
        self.__ancestor_pane = ShadedWidget()
        self.__ancestor_pane.setPalette(self.__alternate_palette)
        self.__ancestor_pane_layout = QFormLayout()
        self.__ancestor_pane_layout.addRow("Entry Ancestor", None)
        self.__ancestor_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.__ancestor_pane.setLayout(self.__ancestor_pane_layout)

        # Raw Pane
        self.__raw_pane = QWidget()
        self.__raw_pane_layout = QFormLayout()
        self.__raw_pane_layout.addRow("Entry", None)
        self.__raw_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.__raw_pane.setLayout(self.__raw_pane_layout)

        # Descendent Pane
        self.__descendent_pane = ShadedWidget()
        self.__descendent_pane.setPalette(self.__alternate_palette)
        self.__descendent_pane_layout = QFormLayout()
        self.__descendent_pane_layout.addRow("Entry Descendent", None)
        self.__descendent_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.__descendent_pane.setLayout(self.__descendent_pane_layout)

        # Add a separator for UX
        self.__separator_1 = QFrame()
        self.__separator_1.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        self.__separator_1.setLineWidth(3)
        self.__separator_1.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")

        # Display pane holder
        self.__display_pane = QWidget()

        # Orientation
        if self.frameGeometry().width() <= self.frameGeometry().height():
            self.__display_pane_layout = QVBoxLayout()
        else:
            self.__display_pane_layout = QHBoxLayout()

        self.__display_pane_layout.addWidget(self.__ancestor_pane)
        self.__display_pane_layout.addWidget(self.__raw_pane)
        self.__display_pane_layout.addWidget(self.__descendent_pane)
        self.__display_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.__display_pane.setLayout(self.__display_pane_layout)

        # Context menu
        self.__display_pane.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.__display_pane.customContextMenuRequested.connect(self.__handle_context_menu)

        # Add a separator for UX
        self.__separator_2 = QFrame()
        self.__separator_2.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        self.__separator_2.setLineWidth(3)
        self.__separator_2.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")

        # Move button group
        self.__move_up_button = QPushButton("Move Up")
        self.__move_up_button.clicked.connect(self.__handle_move_up_callback)
        self.__move_down_button = QPushButton("Move Down")
        self.__move_down_button.clicked.connect(self.__handle_move_down_callback)
        self.__move_to_button = QPushButton("Move To")
        self.__move_to_button.clicked.connect(self.__handle_move_to_callback)
        self.__move_to_field = QLineEdit("")
        self.__move_button_group = QWidget()
        self.__move_button_group_layout = QFormLayout()
        self.__move_button_group_layout.addRow("Move Entry In History Controls", QLabel())
        self.__move_button_group_layout.addRow(self.__move_up_button, None)
        self.__move_button_group_layout.addRow(self.__move_down_button, None)
        self.__move_button_group_layout.addRow(self.__move_to_button, self.__move_to_field)
        self.__move_button_group_layout.setContentsMargins(0, 0, 0, 0)
        self.__move_button_group.setLayout(self.__move_button_group_layout)

        # Manipulation Controls
        self.__set_as_head_button = QPushButton("Set Entry To Current History Index")
        self.__set_as_head_button.clicked.connect(self.__handle_set_as_head_callback)
        self.__edit_button = QPushButton("Edit Entry")
        self.__edit_button.clicked.connect(self.__handle_edit_callback)
        self.__update_button = QPushButton("Update Entry At Current History Index")
        self.__update_button.clicked.connect(self.__handle_update_callback)
        self.__delete_series_button = QPushButton("Delete Series")
        self.__delete_series_button.clicked.connect(self.__handle_delete_series_callback)
        self.__delete_button = QPushButton("Delete Entry")
        self.__delete_button.clicked.connect(self.__handle_delete_callback)
        self.__duplicate_button = QPushButton("Duplicate Entry")
        self.__duplicate_button.clicked.connect(self.__handle_duplicate_callback)
        self.__core_button_group = QWidget()
        self.__core_button_group_layout = QVBoxLayout()
        self.__core_button_group_layout.addWidget(QLabel("Core Controls"))
        self.__core_button_group_layout.addWidget(self.__set_as_head_button)
        self.__core_button_group_layout.addWidget(self.__edit_button)
        self.__core_button_group_layout.addWidget(self.__update_button)
        self.__core_button_group_layout.addWidget(self.__delete_series_button)
        self.__core_button_group_layout.addWidget(self.__delete_button)
        self.__core_button_group_layout.addWidget(self.__duplicate_button)
        self.__core_button_space = QWidget()
        self.__core_button_group_layout.addWidget(self.__core_button_space)
        self.__core_button_group_layout.setStretchFactor(self.__core_button_space, 5)
        self.__core_button_group_layout.setContentsMargins(0, 0, 0, 0)
        self.__core_button_group.setLayout(self.__core_button_group_layout)

        # Control pane
        self.__control_pane = QWidget()
        self.__control_pane_layout = QHBoxLayout()
        self.__control_pane_layout.addStretch()
        self.__control_pane_layout.addWidget(self.__core_button_group)
        self.__control_pane_layout.setStretchFactor(self.__core_button_group, 1)
        self.__control_pane_layout.addWidget(self.__move_button_group)
        self.__control_pane_layout.setStretchFactor(self.__move_button_group, 1)
        self.__control_pane_layout.addStretch()
        self.__control_pane.setLayout(self.__control_pane_layout)

        # Set the layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__display_pane)
        self.__layout.setStretchFactor(self.__display_pane, 2000)
        self.__layout.addWidget(self.__separator_2)
        self.__layout.setStretchFactor(self.__separator_2, 1)
        self.__layout.addWidget(self.__control_pane)
        self.__layout.setStretchFactor(self.__control_pane, 20)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__entry_view.setLayout(self.__layout)

    def fill_content(self):
        self.clear_content()

        self.__fill_character_filter()
        self.__fill_category_selector()
        self.__fill_active_list()
        self.__fill_entry_view()

    def __fill_character_filter(self):
        characters = self.root_gui.runtime.data_manager.get_characters()

        # Regenerate our character filter
        self.__character_filter.blockSignals(True)
        self.__character_filter.clear()

        # Build our list of highlights
        self.__character_filter.addItem("No Character Filter", userData=None)
        for character in characters:
            self.__character_filter.addItem(character.name, userData=character.unique_id)
        self.__character_filter.blockSignals(False)

    def __fill_category_selector(self):
        categories = self.root_gui.runtime.data_manager.get_categories()

        # Regenerate our category filter
        self.__category_filter.blockSignals(True)
        self.__category_filter.clear()

        # Build our list of highlights
        self.__category_filter.addItem("No Category Filter", userData=None)
        for category in categories:
            self.__category_filter.addItem(category.name, userData=category.unique_id)
        self.__category_filter.blockSignals(False)

    def __fill_active_list(self):
        current_index_selected = self.__active_list.currentRow()
        current_entry_selected = None
        if current_index_selected != -1:
            current_entry_selected = self.__active_list.item(current_index_selected).data(Qt.ItemDataRole.UserRole)

        # Get our filters
        character_filter = self.__character_filter.currentData()
        category_filter = self.__category_filter.currentData()

        # Create a list of viable entries - do this outside of this display loop, so we can evaluate the status of our 'current selection'
        valid_entries = list()
        entry_ids = self.root_gui.runtime.data_manager.get_history()
        for entry_id in entry_ids:
            entry = self.root_gui.runtime.data_manager.get_entry_by_id(entry_id)

            # Check our filters
            if character_filter is not None and entry.character_id != character_filter:
                continue
            if category_filter is not None and entry.category_id != category_filter:
                continue

            valid_entries.append(entry_id)

        # Evaluate the status of our current selection - no valid entries == nothing to do
        if len(valid_entries) <= 0:
            return

        # Handle if our pointer changed due to a new filter being applied
        elif current_entry_selected in valid_entries:
            current_index_selected = valid_entries.index(current_entry_selected)

        # Block our signals so we don't trigger any updates
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        current_history_entry = self.root_gui.runtime.data_manager.get_entry_id_by_history_index(self.root_gui.runtime.data_manager.get_current_history_index())
        for index, entry_id in enumerate(valid_entries):
            entry = self.root_gui.runtime.data_manager.get_entry_by_id(entry_id)

            # Check our filters
            if character_filter is not None:
                if entry.character_id != character_filter:
                    continue
            if category_filter is not None:
                if entry.category_id != category_filter:
                    continue

            # Add the string
            display_string = self.root_gui.create_entry_summary_string(entry_id)
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)

            # Get and set the colour
            if entry_id == current_history_entry:
                colour = Qt.GlobalColor.blue
            elif current_entry_selected in self.root_gui.runtime.data_manager.get_entry_revisions_for_id(entry_id):
                colour = Qt.GlobalColor.yellow
            else:
                colour = Qt.GlobalColor.white
            item.setForeground(colour)

            # Set the item
            self.__active_list.addItem(item)

        self.__active_list.setCurrentRow(current_index_selected)  # VERIFY: This doesn't send signals
        self.__active_list.blockSignals(False)

    def __fill_entry_view(self):
        self.__fill_entry_content()
        self.__update_navigations()

    def __fill_entry_content(self):
        # We always need to redraw as the underlying data may have changed
        for row in range(self.__raw_pane_layout.rowCount() - 1):
            self.__raw_pane_layout.removeRow(1)
        for row in range(self.__ancestor_pane_layout.rowCount() - 1):
            self.__ancestor_pane_layout.removeRow(1)
        for row in range(self.__descendent_pane_layout.rowCount() - 1):
            self.__descendent_pane_layout.removeRow(1)

        # Obtain the currently selected item and bail if there's nothing
        item = self.__active_list.currentItem()
        if item is None:
            self.selected_entry_id = None
            return

        # Current state
        self.selected_entry_id = item.data(Qt.ItemDataRole.UserRole)
        entry = self.root_gui.runtime.data_manager.get_entry_by_id(self.selected_entry_id)

        # Gather additional data for this entry
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

        # Draw our 'current' entry
        entry_components.create_entry_form(
            self.root_gui,
            self.__raw_pane_layout,
            character,
            category,
            entry,
            current_index,
            readonly=True,
            translate_with_dynamic_data=should_display_dynamic_data,
            dynamic_data_index=target_index)

        # Display our ancestor entry if pertinent
        target_id = entry.parent_id
        if target_id is not None:
            self.__ancestor_pane.show()
            ancestor = self.root_gui.runtime.data_manager.get_entry_by_id(target_id)
            ancestor_index = self.root_gui.runtime.data_manager.get_entry_index_in_history(target_id)
            entry_components.create_entry_form(
                self.root_gui,
                self.__ancestor_pane_layout,
                character,
                category,
                ancestor,
                ancestor_index,
                readonly=True,
                translate_with_dynamic_data=should_display_dynamic_data,
                dynamic_data_index=target_index)
        else:
            self.__ancestor_pane.hide()

        # Display our child entry if pertinent
        target_id = entry.child_id
        if target_id is not None:
            self.__descendent_pane.show()
            descendent = self.root_gui.runtime.data_manager.get_entry_by_id(target_id)
            descendent_index = self.root_gui.runtime.data_manager.get_entry_index_in_history(target_id)
            entry_components.create_entry_form(
                self.root_gui,
                self.__descendent_pane_layout,
                character, category,
                descendent,
                descendent_index,
                readonly=True,
                translate_with_dynamic_data=should_display_dynamic_data,
                dynamic_data_index=target_index)
        else:
            self.__descendent_pane.hide()

    def __update_navigations(self):
        if self.selected_entry_id is None or self.__active_list.currentIndex() == 0:
            self.__move_up_button.setEnabled(False)
        else:
            self.__move_up_button.setEnabled(True)

        # Move entry down button
        if self.selected_entry_id is None or self.__active_list.currentIndex() == self.root_gui.runtime.data_manager.get_length_of_history() - 1:
            self.__move_down_button.setEnabled(False)
        else:
            self.__move_down_button.setEnabled(True)

        # Move to:
        if self.selected_entry_id is None and self.__active_list.count() == 1:
            self.__move_to_button.setEnabled(False)
        else:
            self.__move_to_button.setEnabled(True)

        # Get the current index in our history for our 'move to' indicator
        head_index = self.root_gui.runtime.data_manager.get_current_history_index()
        self.__move_to_field.setText(str(head_index))

    def clear_content(self):
        self.blockSignals(True)
        self.__character_filter.clear()
        self.__category_filter.clear()
        self.__active_list.clear()
        self.selected_entry_id = None
        self.__fill_entry_view()  # Should clear based on us having no selection
        self.blockSignals(False)

    def __handle_filter_changed_callback(self):
        self.__fill_active_list()

    def __handle_sidebar_selection_changed_callback(self):
        self.__repaint_list()
        self.__fill_entry_view()

    def __repaint_list(self):
        self.__active_list.blockSignals(True)
        current_index_selected = self.__active_list.currentRow()
        current_entry_selected = self.__active_list.item(current_index_selected).data(Qt.ItemDataRole.UserRole)
        current_history_entry = self.root_gui.runtime.data_manager.get_entry_id_by_history_index(self.root_gui.runtime.data_manager.get_current_history_index())

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

    def __handle_view_dynamic_data_relative_callback(self):
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        if self.view_dynamic_relative and self.view_dynamic_absolute:
            self.__view_dynamic_data_absolute_checkbox.blockSignals(True)
            self.view_dynamic_absolute = not self.view_dynamic_relative
            self.__view_dynamic_data_absolute_checkbox.setChecked(self.view_dynamic_absolute)
            self.__view_dynamic_data_absolute_checkbox.blockSignals(False)
        self.__fill_entry_content()

    def __handle_view_dynamic_data_absolute_callback(self):
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()
        if self.view_dynamic_absolute and self.view_dynamic_relative:
            self.__view_dynamic_data_relative_checkbox.blockSignals(True)
            self.view_dynamic_relative = not self.view_dynamic_absolute
            self.__view_dynamic_data_relative_checkbox.setChecked(self.view_dynamic_relative)
            self.__view_dynamic_data_relative_checkbox.blockSignals(False)
        self.__fill_entry_content()

    def __handle_new_entry_callback(self):
        entry = entry_components.add_entry(self.root_gui)
        if entry is None:
            return

        self.selected_entry_id = entry.unique_id
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

    def __handle_new_output_callback(self):
        output_components.add_or_edit_output(self.root_gui, None)

    def __handle_context_menu(self, pos):
        if self.selected_entry_id is None:
            return

        context_menu = QMenu(self)

        # Create actions for the context menu
        copy_id_to_clipboard_action = QAction("Copy Current Entry ID", self)
        copy_id_to_clipboard_action.triggered.connect(partial(self.root_gui.copy_id_to_clipboard, self.selected_entry_id))
        copy_character_id_to_clipboard_action = QAction("Copy Current Character ID", self)
        copy_character_id_to_clipboard_action.triggered.connect(partial(self.root_gui.copy_character_to_clipboard, self.selected_entry_id))

        # Add actions to the context menu
        context_menu.addAction(copy_id_to_clipboard_action)
        context_menu.addAction(copy_character_id_to_clipboard_action)

        # Show the context menu at the mouse position
        context_menu.exec(self.mapToGlobal(pos))

    def __handle_move_up_callback(self):
        target_index = self.root_gui.runtime.data_manager.get_entry_index_in_history(self.selected_entry_id) - 1
        self.root_gui.runtime.data_manager.move_entry_to(self.selected_entry_id, target_index)
        self.__handle_data_changed()
        self.__update_navigations()

    def __handle_move_down_callback(self):
        target_index = self.root_gui.runtime.data_manager.get_entry_index_in_history(self.selected_entry_id) + 1
        self.root_gui.runtime.data_manager.move_entry_to(self.selected_entry_id, target_index)
        self.__handle_data_changed()
        self.__update_navigations()

    def __handle_move_to_callback(self):
        try:
            target_index = int(self.__move_to_field.text())
        except ValueError:
            return

        # Check if the index is viable
        if target_index < 0 or target_index >= self.root_gui.runtime.data_manager.get_length_of_history():
            return

        # Engine will handle the dependency reordering
        self.root_gui.runtime.data_manager.move_entry_to(self.selected_entry_id, target_index)
        self.__handle_data_changed()
        self.__update_navigations()

    def __handle_set_as_head_callback(self):
        entry_components.set_entry_as_head(self.root_gui, self.selected_entry_id)
        self.__repaint_list()
        self.__fill_entry_content()

    def __handle_edit_callback(self):
        entry_components.edit_entry(self.root_gui, self, self.selected_entry_id)
        self.__fill_active_list()  # In case our summary data changed
        self.__fill_entry_content()

    def __handle_update_callback(self):
        updated_entry = entry_components.update_entry(self.root_gui, self, self.selected_entry_id)
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
