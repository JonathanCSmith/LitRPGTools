import abc
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QLabel, QFormLayout, QPushButton, QLineEdit, QFrame, QScrollArea, QTabWidget, QMessageBox

from new.data import Entry, Category, Output
from new.ui.desktop import widget_factories, gui_actions

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


class Tab(QWidget):
    __metaclass__ = abc.ABCMeta

    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(Tab, self).__init__()
        self._parent = parent
        self._engine = engine

        # All tab props
        self.setContentsMargins(0, 0, 0, 0)

    @abc.abstractmethod
    def handle_update(self):
        pass


class SelectedTab(Tab):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(SelectedTab, self).__init__(parent, engine)
        self.__entry = None
        self.__entry_index = None
        self.__ancestor_pointer = 1
        self.__descendent_pointer = 1

        # Ancestor Pane
        self.__ancestor_pane = QWidget()
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
        self.__descendent_pane = QWidget()
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

        # Ancestor button group
        # self.__older_ancestor_button = QPushButton("Older Ancestor")
        # self.__older_ancestor_button.clicked.connect(self.__handle_older_ancestor_callback)
        # self.__younger_ancestor_button = QPushButton("Younger Ancestor")
        # self.__younger_ancestor_button.clicked.connect(self.__handle_younger_ancestor_callback)
        # self.__ancestor_button_group = QWidget()
        # self.__ancestor_button_group_layout = QVBoxLayout()
        # self.__ancestor_button_group_layout.addWidget(QLabel("Ancestor View Controls"))
        # self.__ancestor_button_group_layout.addWidget(self.__older_ancestor_button)
        # self.__ancestor_button_group_layout.addWidget(self.__younger_ancestor_button)
        # self.__ancestor_button_space = QWidget()
        # self.__ancestor_button_group_layout.addWidget(self.__ancestor_button_space)
        # self.__ancestor_button_group_layout.setStretchFactor(self.__ancestor_button_space, 5)
        # self.__ancestor_button_group_layout.setContentsMargins(0, 0, 0, 0)
        # self.__ancestor_button_group.setLayout(self.__ancestor_button_group_layout)

        # Descendent button group
        # self.__older_descendent_button = QPushButton("Older Descendent")
        # self.__older_descendent_button.clicked.connect(self.__handle_older_descendent_callback)
        # self.__younger_descendent_button = QPushButton("Younger Descendent")
        # self.__younger_descendent_button.clicked.connect(self.__handle_younger_descendent_callback)
        # self.__descendent_button_group = QWidget()
        # self.__descendent_button_group_layout = QVBoxLayout()
        # self.__descendent_button_group_layout.addWidget(QLabel("Descendent View Controls"))
        # self.__descendent_button_group_layout.addWidget(self.__older_descendent_button)
        # self.__descendent_button_group_layout.addWidget(self.__younger_descendent_button)
        # self.__descendent_button_space = QWidget()
        # self.__descendent_button_group_layout.addWidget(self.__descendent_button_space)
        # self.__descendent_button_group_layout.setStretchFactor(self.__descendent_button_space, 5)
        # self.__descendent_button_group_layout.setContentsMargins(0, 0, 0, 0)
        # self.__descendent_button_group.setLayout(self.__descendent_button_group_layout)

        # Manipulation Controls
        self.__set_as_head_button = QPushButton("Set As Current Entry in History")
        self.__set_as_head_button.clicked.connect(self.__handle_set_as_head_callback)
        self.__set_as_selected_button = QPushButton("Highlight all entries in series.")
        self.__set_as_selected_button.clicked.connect(self.__handle_set_as_selected_callback)
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
        self.__core_button_group_layout.addWidget(self.__set_as_selected_button)
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
        self.__control_pane_spacer_1 = QWidget()
        self.__control_pane_layout.addWidget(self.__control_pane_spacer_1)
        self.__control_pane_layout.setStretchFactor(self.__control_pane_spacer_1, 5)
        self.__control_pane_layout.addWidget(self.__core_button_group)
        self.__control_pane_layout.setStretchFactor(self.__core_button_group, 1)
        self.__control_pane_layout.addWidget(self.__move_button_group)
        self.__control_pane_layout.setStretchFactor(self.__move_button_group, 1)
        # self.__control_pane_layout.addWidget(self.__ancestor_button_group)
        # self.__control_pane_layout.setStretchFactor(self.__ancestor_button_group, 1)
        # self.__control_pane_layout.addWidget(self.__descendent_button_group)
        # self.__control_pane_layout.setStretchFactor(self.__descendent_button_group, 1)
        self.__control_pane_spacer_2 = QWidget()
        self.__control_pane_layout.addWidget(self.__control_pane_spacer_2)
        self.__control_pane_layout.setStretchFactor(self.__control_pane_spacer_2, 5)
        self.__control_pane_layout.setContentsMargins(0, 0, 0, 0)
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
        self.handle_update()

    def __handle_move_up_callback(self):
        # Check the validity of our cache
        if self.__entry is not None and self.__entry_index is not None:

            # Engine will handle the dependency reordering
            self._engine.move_entry_to(self.__entry, self.__entry_index - 1)
            self._parent.set_curently_selected(self.__entry_index - 1)
            self._parent.handle_update()

    def __handle_move_down_callback(self):
        # Check the validity of our cache
        if self.__entry is not None and self.__entry_index is not None:

            # Engine will handle the dependency reordering
            self._engine.move_entry_to(self.__entry, self.__entry_index + 1)
            self._parent.set_curently_selected(self.__entry_index + 1)
            self._parent.handle_update()

    def __handle_move_to_callback(self):
        # Check the validity of our cache
        if self.__entry is not None and self.__entry_index is not None:
            try:
                target_index = int(self.__move_to_field.text())
            except:
                return

            # Check if the index is viable
            if target_index >= 0 or target_index < self._engine.get_length_of_history():
                return

            # Engine will handle the dependency reordering
            self._engine.move_entry_to(self.__entry, target_index)
            self._parent.set_curently_selected(target_index)
            self._parent.handle_update()

    def __handle_older_ancestor_callback(self):
        self.__ancestor_pointer += 1
        self.handle_update()  # No need to trigger a global update here

    def __handle_younger_ancestor_callback(self):
        if self.__ancestor_pointer > 1:
            self.__ancestor_pointer -= 1
            self.handle_update()

    def __handle_older_descendent_callback(self):
        if self.__descendent_pointer > 1:
            self.__descendent_pointer -= 1
            self.handle_update()

    def __handle_younger_descendent_callback(self):
        self.__descendent_pointer += 1
        self.handle_update()

    def __handle_set_as_head_callback(self):
        gui_actions.set_entry_as_head(self._engine, self._parent, self.__entry)

    def __handle_set_as_selected_callback(self):
        self._parent.set_curently_selected(self.__entry_index)

    def __handle_edit_callback(self):
        gui_actions.add_or_edit_entry(self._engine, self._parent, self.__entry)

    def __handle_update_callback(self):
        gui_actions.update_entry(self._engine, self._parent, self.__entry)

    def __handle_delete_series_callback(self):
        gui_actions.delete_entry_series(self._engine, self._parent, self.__entry)

    def __handle_delete_callback(self):
        gui_actions.delete_entry(self._engine, self._parent, self.__entry)

    def __handle_duplicate_callback(self):
        gui_actions.duplicate_entry(self._engine, self._parent, self.__entry)

    def handle_update(self):
        # Obtain the currently selected item and bail if there's nothing
        item = self._parent.get_currently_selected()
        if item is None:
            self.hide()
            return
        current_entry_id = item.data(Qt.ItemDataRole.UserRole)
        if current_entry_id is None:
            self.hide()
            return
        entry = self._engine.get_entry_by_id(current_entry_id)
        if entry is None:
            self.hide()
            return

        # Show our layout now
        self.show()

        # Get the current index in our history
        index = self._engine.get_entry_index_in_history(current_entry_id)
        if index is None:
            return
        self.__move_to_field.setText(str(index))

        # We always need to redraw as the underlying data may have changed
        for row in range(self.__raw_pane_layout.rowCount()):
            self.__raw_pane_layout.removeRow(0)
        for row in range(self.__ancestor_pane_layout.rowCount()):
            self.__ancestor_pane_layout.removeRow(0)
        for row in range(self.__descendent_pane_layout.rowCount()):
            self.__descendent_pane_layout.removeRow(0)

        # Set our internal caches
        self.__entry = entry
        self.__entry_index = index

        # Get additional data
        character = self._engine.get_character_by_id(entry.character_id)
        category = self._engine.get_category_by_id(entry.category_id)

        # Draw our 'current' entry
        entry_index = self._engine.get_entry_index_in_history(current_entry_id)
        widget_factories.create_entry_form(self.__raw_pane_layout, character, category, entry, entry_index, readonly=True)

        # Hide the ancestor/descendent panes whent their aren't any
        if entry.parent_id is None:
            self.__ancestor_pane.hide()
            # self.__ancestor_button_group.hide()
        else:
            self.__ancestor_pane.show()
            # self.__ancestor_button_group.show()
        if entry.child_id is None:
            self.__descendent_pane.hide()
            # self.__descendent_button_group.hide()
        else:
            self.__descendent_pane.show()
            # self.__descendent_button_group.show()

        # Calculate our ancestor
        counter = self.__ancestor_pointer
        target_id = entry.unique_id
        while counter >= 1 and target_id is not None:
            rolling_target = self._engine.get_entry_by_id(target_id)
            target_id = rolling_target.parent_id
            counter -= 1
        if target_id is not None:
            ancestor = self._engine.get_entry_by_id(target_id)
            ancestor_index = self._engine.get_entry_index_in_history(target_id)
            widget_factories.create_entry_form(self.__ancestor_pane_layout, character, category, ancestor, ancestor_index, readonly=True)

        # Calculate our descendent
        counter = self.__descendent_pointer
        target_id = entry.unique_id
        while counter >= 1 and target_id is not None:
            rolling_target = self._engine.get_entry_by_id(target_id)
            target_id = rolling_target.child_id
            counter -= 1
        if target_id is not None:
            descendent = self._engine.get_entry_by_id(target_id)
            descendent_index = self._engine.get_entry_index_in_history(target_id)
            widget_factories.create_entry_form(self.__descendent_pane_layout, character, category, descendent, descendent_index, readonly=True)


class SearchTab(Tab):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(SearchTab, self).__init__(parent, engine)
        self.__results = None

        # Search bar
        self.__search_bar = QLineEdit()
        self.__search_button = QPushButton("Search")
        self.__search_button.clicked.connect(self.__handle_search_callback)
        self.__search_group = QWidget()
        self.__search_group_layout = QHBoxLayout()
        self.__search_group_layout.addWidget(self.__search_bar)
        self.__search_group_layout.setStretchFactor(self.__search_bar, 5)
        self.__search_group_layout.addWidget(self.__search_button)
        self.__search_group_layout.setStretchFactor(self.__search_button, 1)
        self.__search_group_layout.setContentsMargins(0, 0, 0, 0)
        self.__search_group.setLayout(self.__search_group_layout)

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
        self.__layout.addWidget(self.__search_group)
        self.__layout.addWidget(self.__results_view_scroll)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def __handle_search_callback(self):
        # Clear our current results
        for i in reversed(range(self.__results_view_layout.count())):
            w = self.__results_view_layout.itemAt(i).widget()
            self.__results_view_layout.removeWidget(w)
            w.deleteLater()

        # Get our search data
        search_text = self.__search_bar.text()
        if search_text is None or search_text == "":
            return

        # Draw our results
        self.__results = self._engine.search_all(search_text)
        for result in self.__results:
            # Currently we only support entries and categories.
            if isinstance(result, Entry):
                widget_factories.create_entry_form_with_controls(self.__results_view_layout, self._engine, self._parent, result)

            elif isinstance(result, Category):
                self.__draw_category(result)

        # Spacer
        spacer = QWidget()
        self.__results_view_layout.addWidget(spacer)
        self.__results_view_layout.setStretchFactor(spacer, 100)

    def __draw_category(self, category: Category):
        # Form
        category_form = QWidget()
        category_form_layout = QFormLayout()
        widget_factories.create_category_form(category_form_layout, category)
        category_form.setLayout(category_form_layout)

        # Controls
        category_controls = QWidget()
        category_controls_layout = QVBoxLayout()
        category_edit_button = QPushButton("Edit")
        category_edit_button.clicked.connect(partial(gui_actions.add_or_edit_category, self._engine, self._parent, category))
        category_controls_layout.addWidget(category_edit_button)
        category_delete_button = QPushButton("Delete")
        category_delete_button.clicked.connect(partial(gui_actions.delete_category, self._engine, self._parent, category))
        category_controls_layout.addWidget(category_delete_button)
        spacer = QWidget()
        category_controls_layout.addWidget(spacer)
        category_controls_layout.setStretchFactor(spacer, 100)
        category_controls_layout.setContentsMargins(0, 0, 0, 0)
        category_controls.setLayout(category_controls_layout)

        # Main container
        category_widget = QWidget()
        category_widget_layout = QHBoxLayout()
        category_widget_layout.addWidget(category_form)
        category_widget_layout.setStretchFactor(category_form, 90)
        category_widget_layout.addWidget(category_controls)
        category_widget_layout.setStretchFactor(category_controls, 10)
        category_widget_layout.setContentsMargins(0, 0, 0, 0)
        category_widget.setObjectName("bordered")
        category_widget.setLayout(category_widget_layout)
        self.__results_view_layout.addWidget(category_widget)

    def handle_update(self):
        self.__handle_search_callback()


class OutputsTab(Tab):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super(OutputsTab, self).__init__(parent, engine)

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
        self.__layout.addWidget(self.__results_view_scroll)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def handle_update(self):
        # Clear our current results
        for i in reversed(range(self.__results_view_layout.count())):
            w = self.__results_view_layout.itemAt(i).widget()
            self.__results_view_layout.removeWidget(w)
            w.deleteLater()

        # Bail if there are no views currently
        results = self._engine.get_outputs()
        if results is None or len(results) == 0:
            return

        # Create new entries for the view
        for output in results:
            self.__draw_output(output)

    def __draw_output(self, output: Output):
        history_indices = []
        for entry in output.members:
            history_indices.append(str(self._engine.get_entry_index_in_history(entry)))

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
        basic_props_widget.setLayout(basic_props_widget)
        output_layout.addWidget(basic_props_widget)

        # Spacer
        separator = QFrame()
        separator.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Raised)
        separator.setLineWidth(3)
        separator.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        output_layout.addWidget(separator)

        # Render the entries that are actually included in our output ONLY
        for current_index, result_id in enumerate(output.members):
            entry = self._engine.get_entry_by_id(result_id)

            # Details
            character = self._engine.get_character_by_id(entry.character_id)
            category = self._engine.get_category_by_id(entry.category_id)
            entry_index = self._engine.get_entry_index_in_history(entry.unique_id)

            # Form
            entry_form = QWidget()
            entry_form_layout = QFormLayout()
            widget_factories.create_entry_form(entry_form_layout, character, category, entry, entry_index)
            entry_form.setLayout(entry_form_layout)
            output_layout.addWidget(entry_form)

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
        output_edit_button.clicked.connect(partial(gui_actions.add_or_edit_output, self._engine, self._parent, output))
        output_controls_layout.addWidget(output_edit_button)
        output_delete_button = QPushButton("Delete")
        output_delete_button.clicked.connect(partial(gui_actions.delete_output, self._engine, self._parent, output))
        output_controls_layout.addWidget(output_delete_button)
        spacer = QWidget()
        output_controls_layout.addWidget(spacer)
        output_controls_layout.setStretchFactor(spacer, 100)
        output_controls_layout.setContentsMargins(0, 0, 0, 0)
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

    def __handle_move_output_up_callback(self, output: Output):
        outcome = QMessageBox.question(self, "Are you sure?", "This will remove an entry from your Output and add it to any subsequent Outputs. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if not outcome:
            return

        self._engine.move_output_up_by_id(output.unique_id)
        self._parent.handle_update()

    def __handle_move_output_down_callback(self, output: Output):
        outcome = QMessageBox.question(self, "Are you sure?", "This will remove an entry from any subsequent Output and add it to this Output. Are you certain?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if not outcome:
            return

        self._engine.move_output_down_by_id(output.unique_id)
        self._parent.handle_update()


class CharacterTab(Tab):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine', character_id: str):
        super(CharacterTab, self).__init__(parent, engine)
        self.__character_id = character_id

        # Content
        self.__tabbed_view = QTabWidget()
        self.__tabbed_view.currentChanged.connect(self.__handle_tab_changed_callback)

        # Additional tabs
        self.__tabs_cache = OrderedDict()

        # Layout
        self.__layout = QVBoxLayout()
        self.__layout.addWidget(self.__tabbed_view)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.setStretch(0, 100000)
        self.setLayout(self.__layout)

    def __handle_tab_changed_callback(self):
        tabbed_widget = self.__tabbed_view.currentWidget()
        if tabbed_widget is None:
            return
        tabbed_widget.handle_update()

    def handle_update(self):
        current_tab_index = self.__tabbed_view.currentIndex()
        current_tab_text = self.__tabbed_view.tabText(current_tab_index)

        # Block notifications
        self.__tabbed_view.blockSignals(True)

        # Refresh our tabs and store them in a list for comparison
        self.__tabbed_view.clear()
        category_ids = self._engine.get_categories_for_character_id(self.__character_id)
        if category_ids is None:
            return

        for category_id in category_ids:
            category = self._engine.get_category_by_id(category_id)

            # Retrieve cached tab and add to tabs
            if category_id in self.__tabs_cache:
                tab = self.__tabs_cache[category_id]
            else:
                tab = CategoryTab(self._parent, self._engine, self.__character_id, category_id)
            self.__tabbed_view.addTab(tab, category.name)

        # Remove redundant cached items
        items_to_delete = []
        for category_id in self.__tabs_cache.keys():
            if category_id not in category_ids:
                items_to_delete.append(category_id)
        for item in items_to_delete:
            self.__tabs_cache[item].deleteLater()
            del self.__tabs_cache[item]

        # Return to selected if possible
        keys = self.__tabs_cache.keys()
        if current_tab_text in keys:
            index = keys.index(current_tab_index)
            self.__tabbed_view.setCurrentIndex(index)

        # Return signals
        self.__tabbed_view.blockSignals(False)

        # defer update to tab
        w = self.__tabbed_view.currentWidget()
        if w is not None:
            w.handle_update()


class CategoryTab(Tab):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine', character_id: str, category_id: str):
        super(CategoryTab, self).__init__(parent, engine)
        self.__character_id = character_id
        self.__category_id = category_id

        # Control bar
        self.__control_bar = QWidget()
        self.__move_character_tab_left_button = QPushButton("Move Current Character Tab Left")
        self.__move_character_tab_left_button.clicked.connect(partial(self._engine.move_character_id_left, self.__character_id))
        self.__move_character_tab_right_button = QPushButton("Move Current Character Tab Right")
        self.__move_character_tab_right_button.clicked.connect(partial(self._engine.move_character_id_right, self.__character_id))
        self.__move_category_tab_left_button = QPushButton("Move Current Category Tab Left")
        self.__move_category_tab_left_button.clicked.connect(partial(self._engine.move_category_id_left, self.__category_id))
        self.__move_category_tab_right_button = QPushButton("Move Current Category Tab Right")
        self.__move_category_tab_right_button.clicked.connect(partial(self._engine.move_category_id_right, self.__category_id))
        self.__control_bar_layout = QHBoxLayout()
        self.__control_bar_layout.addWidget(self.__move_character_tab_left_button)
        self.__control_bar_layout.addWidget(self.__move_character_tab_right_button)
        self.__control_bar_layout.addWidget(self.__move_category_tab_left_button)
        self.__control_bar_layout.addWidget(self.__move_category_tab_right_button)
        self.__control_bar.setLayout(self.__control_bar_layout)

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
        self.__layout.addWidget(self.__control_bar)
        self.__layout.addWidget(self.__results_view_scroll)
        self.__layout.setStretch(1, 100)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def handle_update(self):
        # Clear our current results
        for i in reversed(range(self.__results_view_layout.count())):
            w = self.__results_view_layout.itemAt(i).widget()
            self.__results_view_layout.removeWidget(w)
            w.deleteLater()

        # Get our entry state for current head
        entries = self._engine.get_entries_for_character_and_category_at_current_history_index(self.__character_id, self.__category_id)
        if entries is None:
            return

        # Display each entry!
        display_hidden = self._parent.get_should_display_hidden()
        for entry_id in entries:
            entry = self._engine.get_entry_by_id(entry_id)

            # Do not display hidden entries when appropriate
            if entry.is_disabled and not display_hidden:
                continue

            widget_factories.create_entry_form_with_controls(self.__results_view_layout, self._engine, self._parent, entry)

        # Spacer
        spacer = QWidget()
        self.__results_view_layout.addWidget(spacer)
        self.__results_view_layout.setStretchFactor(spacer, 100)
