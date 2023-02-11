from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout, QLineEdit, QFrame, QListWidgetItem, QListWidget, QAbstractItemView, QCheckBox

from new.data import Character, Category, Entry
from new.ui.desktop import entry_components, output_components
from new.ui.desktop.custom_generic_components import VisibleDynamicSplitPanel, ShadedWidget

if TYPE_CHECKING:
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI
    from new.main import LitRPGToolsEngine


class HistoryTab(VisibleDynamicSplitPanel):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Main components
        self._sidebar_widget = HistorySidebar(self, engine)
        self._view_widget = HistoryView(self, engine)

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

    def get_currently_selected(self) -> QListWidgetItem | None:
        return self._sidebar_widget.get_currently_selected()

    def set_curently_selected(self, index: int):
        self._sidebar_widget.set_currently_selected(index)

    def get_should_display_dynamic(self):
        return self._sidebar_widget.get_should_display_dynamic()

    def _selection_changed(self):
        self._view_widget.draw()

    def get_should_display_dynamic_absolute(self):
        return self._sidebar_widget.view_dynamic_absolute

    def get_should_display_dynamic_relative(self):
        return self._sidebar_widget.view_dynamic_relative


class HistorySidebar(QWidget):
    def __init__(self, parent: HistoryTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Allow Selection of what we want to display in the sidebar
        # self.__highlight_selector = QComboBox()
        # self.__highlight_selector.currentTextChanged.connect(self.__handle_sidebar_focus_changed_callback)

        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # New entry button
        self.__new_entry_button = QPushButton("Create Entry at Current History Index")
        self.__new_entry_button.clicked.connect(self.__handle_new_entry_callback)

        # New view button
        self.__new_view_button = QPushButton("Create Output at Current History Index")
        self.__new_view_button.clicked.connect(self.__handle_new_output_callback)

        # 'View' buttons
        self.__view_dynamic_data_relative_checkbox = QCheckBox("View Dynamic Data (Respect Current History Index)")
        self.__view_dynamic_data_relative_checkbox.clicked.connect(self.__handle_view_dynamic_data_relative_callback)
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        self.__view_dynamic_data_absolute_checkbox = QCheckBox("View Dynamic Data (Respect Entry Index)")
        self.__view_dynamic_data_absolute_checkbox.clicked.connect(self.__handle_view_dynamic_data_absolute_callback)
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()

        # Layout
        self.__layout = QVBoxLayout()
        # self.__layout.addWidget(QLabel("Current Highlight:"))
        # self.__layout.addWidget(self.__highlight_selector)
        self.__layout.addWidget(self.__active_list)
        self.__layout.addWidget(self.__new_entry_button)
        self.__layout.addWidget(self.__new_view_button)
        self.__layout.addWidget(self.__view_dynamic_data_relative_checkbox)
        self.__layout.addWidget(self.__view_dynamic_data_absolute_checkbox)
        self.setLayout(self.__layout)
        self.setContentsMargins(0, 0, 0, 0)

    # def __handle_sidebar_focus_changed_callback(self):
    #     self._parent.handle_update()
    #
    #     # Set our currently selected to the end to save on some headaches or obtuse logic
    #     self.__active_list.setCurrentRow(self.__active_list.count() - 1)

    def __handle_sidebar_selection_changed_callback(self):
        self.__paint_list()
        self._parent._selection_changed()

        # Block signals on the callback whilst we update so no recursion
        # self.__active_list.itemSelectionChanged.disconnect(self.__handle_sidebar_selection_changed_callback)
        # self._parent.handle_update()
        # self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

    def __paint_list(self):
        for i in range(self.__active_list.count()):
            colour = self.__get_list_row_colour_from_context(i)
            self.__active_list.item(i).setForeground(colour)

    def __get_list_row_colour_from_context(self, index) -> Qt.GlobalColor:
        # First check if it's our active 'head'
        if self._engine.get_current_history_index() == index:
            return Qt.GlobalColor.blue

        current_item = self.__active_list.currentItem()
        if current_item is None:
            print("THIS IS A BUG")

        # Check for a familial relationship with the currently selected
        entry_id = current_item.data(Qt.ItemDataRole.UserRole)
        familial_relatives = self._engine.get_entry_revisions_for_id(entry_id)
        if self.__active_list.item(index).data(Qt.ItemDataRole.UserRole) in familial_relatives:
            return Qt.GlobalColor.yellow

        return Qt.GlobalColor.white

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

    def __handle_new_entry_callback(self):
        entry_components.add_entry(self._engine)
        entry_index = self._engine.get_current_history_index()
        self._parent.draw()
        self._parent.set_curently_selected(entry_index)

    def __handle_new_output_callback(self):
        output_components.add_or_edit_output(self._engine, self, None)
        self._parent.draw()

    def draw(self):
        # # Handle initial case
        # if self.__highlight_selector.currentText() is None or self.__highlight_selector.currentText() == "":
        #     self.__fill_highlight_selector()
        #
        # # Recreate and ensure we are on the correct selection
        # else:
        #     currently_selected = self.__highlight_selector.currentText()
        #     self.__fill_highlight_selector(selected=currently_selected)

        # Fill our list
        self.__fill_active_list()

    # def __fill_highlight_selector(self, selected="History"):
    #     outputs = self._engine.get_outputs()
    #
    #     # Block signalling & clear
    #     self.__highlight_selector.blockSignals(True)
    #     self.__highlight_selector.clear()
    #
    #     # Add in our default view
    #     self.__highlight_selector.addItem("Full History")
    #
    #     # Loop through outputs and add their ids as data - also search for matches in terms of selection
    #     found = False
    #     for index, output in enumerate(outputs):
    #         self.__highlight_selector.addItem(output.name)
    #         self.__highlight_selector.setItemData(index + 1, output.unique_id, Qt.ItemDataRole.UserRole)
    #
    #         # Mark that we have a match for our selected view
    #         if output.name == selected:
    #             found = True
    #
    #     # Special case when a view was deleted and previously selected
    #     if not found:
    #         selected = "Full History"
    #     self.__highlight_selector.setCurrentText(selected)
    #
    #     # Return signalling
    #     self.__highlight_selector.blockSignals(False)
    #
    #     # Update our context flag
    #     self.is_viewing_history = selected == "Full History"

    def __fill_active_list(self):
        # Get the current selection
        current_selection = self.__active_list.currentRow()

        # Switch what information we populate our list with depending on the view selector
        self.__fill_list(self._engine.get_history())

        # Handle the unique case where we added our first entry
        if current_selection == -1 and self._engine.get_length_of_history() > 0:
            current_selection = 0

        # Force an update so our text colour can be rendered
        self.__active_list.setCurrentRow(current_selection)

    def __fill_list(self, entries):
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        for index, entry_id in enumerate(entries):
            entry = self._engine.get_entry_by_id(entry_id)
            category = self._engine.get_category_by_id(entry.category_id)
            character = self._engine.get_character_by_id(entry.character_id)

            # Display string format
            if entry.parent_id is None:
                display_string = category.creation_text
            else:
                display_string = category.update_text
            display_string = self.__fill_display_string(display_string, index, character, category, entry)

            # Add the string
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, entry_id)
            self.__active_list.addItem(item)
        self.__active_list.blockSignals(False)

    def __fill_display_string(self, template_string: str, index: int, character: Character, category: Category, entry: Entry):
        string_result = template_string.format(*entry.data)  # TODO! Codify some nice stuff here
        return "[" + str(index) + "] (" + character.name + "): " + string_result

    def get_currently_selected(self) -> QListWidgetItem | None:
        return self.__active_list.currentItem()

    def set_currently_selected(self, index):
        self.__active_list.setCurrentRow(index)

    def get_should_display_dynamic(self):
        return self.view_dynamic_relative


class HistoryView(QWidget):
    def __init__(self, parent: HistoryTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Currently selected
        self.entry = None
        self.entry_index = None

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

        # Calculate primary orientation
        layout = 0
        if self._parent.frameGeometry().width() > self._parent.frameGeometry().height():
            layout = 1

        # Display pane holder
        self.__display_pane = QWidget()
        if layout == 0:
            self.__display_pane_layout = QVBoxLayout()
        else:
            self.__display_pane_layout = QHBoxLayout()
        self.__display_pane_layout.addWidget(self.__ancestor_pane)
        self.__display_pane_layout.addWidget(self.__raw_pane)
        self.__display_pane_layout.addWidget(self.__descendent_pane)
        self.__display_pane_layout.setContentsMargins(0, 0, 0, 0)
        self.__display_pane.setLayout(self.__display_pane_layout)

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
        self.__set_as_head_button = QPushButton("Set As Current Entry in History")
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
        self.setLayout(self.__layout)

        # Force update
        self.draw()

    def __handle_move_up_callback(self):
        # Check the validity of our cache
        if self.entry is not None and self.entry_index is not None:

            # Engine will handle the dependency reordering
            self._engine.move_entry_to(self.entry, self.entry_index - 1)
            self._parent.set_curently_selected(self.entry_index - 1)
            self._parent.draw()

    def __handle_move_down_callback(self):
        # Check the validity of our cache
        if self.entry is not None and self.entry_index is not None:

            # Engine will handle the dependency reordering
            self._engine.move_entry_to(self.entry, self.entry_index + 1)
            self._parent.set_curently_selected(self.entry_index + 1)
            self._parent.draw()

    def __handle_move_to_callback(self):
        # Check the validity of our cache
        if self.entry is not None and self.entry_index is not None:
            try:
                target_index = int(self.__move_to_field.text())
            except:
                return

            # Check if the index is viable
            if target_index < 0 or target_index >= self._engine.get_length_of_history():
                return

            # Engine will handle the dependency reordering
            self._engine.move_entry_to(self.entry, target_index)
            self._parent.set_curently_selected(target_index)
            self._parent.draw()

    def __handle_set_as_head_callback(self):
        entry_components.set_entry_as_head(self._engine, self.entry)
        self._parent.draw()

    def __handle_set_as_selected_callback(self):
        self._parent.set_curently_selected(self.entry_index)

    def __handle_edit_callback(self):
        entry_components.edit_entry(self._engine, self, self.entry)
        self._parent.draw()

    def __handle_update_callback(self):
        update = entry_components.update_entry(self._engine, self, self.entry)
        if update is not None:
            self._parent.draw()
            self._parent.set_curently_selected(self._engine.get_entry_index_in_history(update.unique_id))

    def __handle_delete_series_callback(self):
        entry_components.delete_entry_series(self._engine, self, self.entry)
        self._parent.draw()
        self._parent.set_curently_selected(self._engine.get_current_history_index())

    def __handle_delete_callback(self):
        entry_components.delete_entry(self._engine, self, self.entry)
        self._parent.draw()
        self._parent.set_curently_selected(self._engine.get_current_history_index())

    def __handle_duplicate_callback(self):
        entry_components.duplicate_entry(self._engine, self.entry)
        self._parent.draw()
        self._parent.set_curently_selected(self._engine.get_current_history_index())

    def draw(self):
        # We always need to redraw as the underlying data may have changed
        for row in range(self.__raw_pane_layout.rowCount()):
            self.__raw_pane_layout.removeRow(0)
        for row in range(self.__ancestor_pane_layout.rowCount()):
            self.__ancestor_pane_layout.removeRow(0)
        for row in range(self.__descendent_pane_layout.rowCount()):
            self.__descendent_pane_layout.removeRow(0)

        # Obtain the currently selected item and bail if there's nothing
        item = self._parent.get_currently_selected()
        if item is None:
            return
        current_entry_id = item.data(Qt.ItemDataRole.UserRole)
        entry = self._engine.get_entry_by_id(current_entry_id)

        # Get the current index in our history
        index = self._engine.get_entry_index_in_history(current_entry_id)
        if index is None:
            return
        self.__move_to_field.setText(str(index))

        # Set our internal caches
        self.entry = entry
        self.entry_index = index

        # Get additional data
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

        # Draw our 'current' entry
        entry_components.create_entry_form(self._engine, self.__raw_pane_layout, character, category, entry, current_index, readonly=True, translate_with_dynamic_data=should_display_dynamic_data, dynamic_data_index=target_index)

        # Hide the ancestor/descendent panes whent their aren't any
        if entry.parent_id is None:
            self.__ancestor_pane.hide()
        else:
            self.__ancestor_pane.show()
        if entry.child_id is None:
            self.__descendent_pane.hide()
        else:
            self.__descendent_pane.show()

        # Calculate our ancestor
        target_id = entry.parent_id
        if target_id is not None:
            ancestor = self._engine.get_entry_by_id(target_id)
            ancestor_index = self._engine.get_entry_index_in_history(target_id)
            entry_components.create_entry_form(self._engine, self.__ancestor_pane_layout, character, category, ancestor, ancestor_index, readonly=True, translate_with_dynamic_data=should_display_dynamic_data, dynamic_data_index=target_index)  # We can use target index here to achieve our desired result

        # Calculate our descendent
        target_id = entry.child_id
        if target_id is not None:
            descendent = self._engine.get_entry_by_id(target_id)
            descendent_index = self._engine.get_entry_index_in_history(target_id)
            entry_components.create_entry_form(self._engine, self.__descendent_pane_layout, character, category, descendent, descendent_index, readonly=True, translate_with_dynamic_data=should_display_dynamic_data, dynamic_data_index=target_index)  # We can use target index here to achieve our desired result
