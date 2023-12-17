from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFormLayout, QPushButton, QHBoxLayout, QListWidget, QAbstractItemView, QLineEdit, QCheckBox, QListWidgetItem

from data.models import Entry, Category
from desktop import entry_components
from desktop.category_components import create_category_form, add_or_edit_category, delete_category
from desktop.custom_generic_components import VisibleDynamicSplitPanel, Content

if TYPE_CHECKING:
    from desktop.guis import DesktopGUI


class SearchTab(VisibleDynamicSplitPanel, Content):
    def __init__(self, root_gui: 'DesktopGUI'):
        super().__init__()
        self.root_gui = root_gui

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

        # Search terms
        self.__search_bar = QLineEdit()
        # self.__replace_bar = QLineEdit()
        self.__search_button = QPushButton("Search")
        self.__search_button.clicked.connect(self.__handle_search_callback)
        self.__search_button.setShortcut("Return")
        # self.__replace_button = QPushButton("Replace Next")
        # self.__replace_button.clicked.connect(self.__handle_replace_single_callback)
        # self.__replace_all_button = QPushButton("Replace All")
        # self.__replace_all_button.clicked.connect(self.__handle_replace_all_callback)

        # View dynamic
        self.__view_dynamic_data_relative_checkbox = QCheckBox("View Dynamic Data (Respect Current History Index)")
        self.__view_dynamic_data_relative_checkbox.clicked.connect(self.__handle_view_dynamic_data_relative_callback)
        self.view_dynamic_relative = self.__view_dynamic_data_relative_checkbox.isChecked()
        self.__view_dynamic_data_absolute_checkbox = QCheckBox("View Dynamic Data (Respect Entry Index)")
        self.__view_dynamic_data_absolute_checkbox.clicked.connect(self.__handle_view_dynamic_data_absolute_callback)
        self.view_dynamic_absolute = self.__view_dynamic_data_absolute_checkbox.isChecked()

        # Layout
        self.__layout = QVBoxLayout()
        # self.__layout.addWidget(self.__highlight_selector)
        self.__layout.addWidget(self.__active_list)
        self.__layout.addWidget(self.__search_bar)
        self.__layout.addWidget(self.__search_button)
        # self.__layout.addWidget(self.__replace_bar)
        # self.__layout.addWidget(self.__replace_button)
        # self.__layout.addWidget(self.__replace_all_button)
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

        self.__fill_search_results()
        self.__fill_entry_view()

    def __fill_search_results(self):
        # Get our search data
        search_text = self.__search_bar.text()
        if search_text is None or search_text == "":
            return

        # Get the results
        results = self.root_gui.runtime.data_manager.search_all(search_text)

        # Block signals and clear list
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        for index, result in enumerate(results):
            if isinstance(result, Entry):
                display_string = self.root_gui.create_entry_summary_string(result.unique_id)

            else:
                display_string = self.root_gui.create_category_summary_string(result.unique_id)

            # Add the string
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, result.unique_id)
            self.__active_list.addItem(item)

        # Return signals
        self.__active_list.blockSignals(False)

    def __fill_entry_view(self):
        # Clear our current data
        result = self.__results_view_layout.itemAt(0)
        if result is not None:
            result_widget = result.widget()
            result_widget.deleteLater()

        # Retrieve our selection
        item = self.__active_list.currentItem()
        if item is None:
            self.selected_entry_id = None
            return
        self.selected_entry_id = item.data(Qt.ItemDataRole.UserRole)

        # Draw the result
        if "category" in item.text():
            result = self.root_gui.runtime.data_manager.get_category_by_id(self.selected_entry_id)
            self.__fill_category_content(result)
        else:
            result = self.root_gui.runtime.data_manager.get_entry_by_id(self.selected_entry_id)
            self.__fill_entry_content(result)

    def __fill_entry_content(self, entry: Entry):
        character = self.root_gui.runtime.data_manager.get_character_by_id(entry.character_id)
        category = self.root_gui.runtime.data_manager.get_category_by_id(entry.category_id)

        # Switch which dynamic data we display depending on what button is ticked
        current_index = self.root_gui.runtime.data_manager.get_entry_index_in_history(entry.unique_id)
        target_index = None
        should_display_dynamic_data = False
        if self.view_dynamic_absolute:
            should_display_dynamic_data = True
        elif self.view_dynamic_relative:
            target_index = self.root_gui.runtime.data_manager.get_current_history_index()
            should_display_dynamic_data = True

        # Form
        entry_form = QWidget()
        entry_form_layout = QFormLayout()
        entry_components.create_entry_form(
            self.root_gui,
            entry_form_layout,
            character,
            category,
            entry,
            current_index,
            header=True,
            readonly=True,
            translate_with_dynamic_data=should_display_dynamic_data,
            dynamic_data_index=target_index)
        entry_form.setLayout(entry_form_layout)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        entry_edit_button = QPushButton("Edit")
        entry_edit_button.clicked.connect(self.__handle_edit_callback)
        entry_controls_layout.addWidget(entry_edit_button)
        entry_update_button = QPushButton("Update")
        entry_update_button.clicked.connect(self.__handle_update_callback)
        entry_controls_layout.addWidget(entry_update_button)
        entry_series_delete_button = QPushButton("Delete Series")
        entry_series_delete_button.clicked.connect(self.__handle_delete_series_callback)
        entry_controls_layout.addWidget(entry_series_delete_button)
        entry_delete_button = QPushButton("Delete")
        entry_delete_button.clicked.connect(self.__handle_delete_callback)
        entry_controls_layout.addWidget(entry_delete_button)
        entry_duplicate_button = QPushButton("Duplicate")
        entry_duplicate_button.clicked.connect(self.__handle_duplicate_callback)
        entry_controls_layout.addWidget(entry_duplicate_button)
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

    def __fill_category_content(self, category: Category):
        # Form
        category_form = QWidget()
        category_form_layout = QFormLayout()
        create_category_form(self.root_gui, category_form_layout, category)
        category_form.setLayout(category_form_layout)

        # Controls
        category_controls = QWidget()
        category_controls_layout = QVBoxLayout()
        category_edit_button = QPushButton("Edit")
        category_edit_button.clicked.connect(partial(add_or_edit_category, self.root_gui, category.unique_id))
        category_controls_layout.addWidget(category_edit_button)
        category_delete_button = QPushButton("Delete")
        category_delete_button.clicked.connect(partial(delete_category, self.root_gui, category.unique_id))
        category_controls_layout.addWidget(category_delete_button)
        category_controls_layout.addStretch()
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

    def clear_content(self):
        self.blockSignals(True)
        self.__search_bar.clear()
        self.__active_list.clear()
        self.selected_entry_id = None
        self.__fill_entry_view()  # Should clear based on us having no item selected
        self.blockSignals(False)

    def __handle_search_callback(self):
        self.__fill_search_results()

    def __handle_sidebar_selection_changed_callback(self):
        self.__fill_entry_view()

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

    def __handle_edit_callback(self):
        entry_components.edit_entry(self.root_gui, self, self.selected_entry_id)
        self.__fill_search_results()
        self.__fill_entry_view()

    def __handle_update_callback(self):
        update = entry_components.update_entry(self.root_gui, self, self.selected_entry_id)
        self.__fill_search_results()

        # Point to our newly created obj
        target_index = 0
        for i in range(self.__active_list.count()):
            potential_match = self.__active_list.item(i).data(Qt.ItemDataRole.UserRole)
            if potential_match == update.unique_id:
                target_index = i

        # Try again if we didn't find our update in our search
        if target_index == 0:
            for i in range(self.__active_list.count()):
                potential_match = self.__active_list.item(i).data(Qt.ItemDataRole.UserRole)
                if potential_match == self.selected_entry_id:
                    target_index = i

        self.__active_list.setCurrentRow(target_index)
        self.__fill_entry_view()

    def __handle_delete_series_callback(self):
        entry_components.delete_entry_series(self.root_gui, self.selected_entry_id)
        self.selected_entry_id = None
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_data_changed(self):
        # Update the GUI
        self.__fill_search_results()

        # Search our history list for the entry, retarget our pointer, repaint accordingly
        self.blockSignals(True)
        target_index = 0
        for i in range(self.__active_list.count()):
            potential_match = self.__active_list.item(i).data(Qt.ItemDataRole.UserRole)
            if potential_match == self.selected_entry_id:
                target_index = i
                break
        self.__active_list.setCurrentRow(target_index)
        self.blockSignals(False)

    def __handle_delete_callback(self):
        entry_components.delete_entry(self.root_gui, self.selected_entry_id)
        self.selected_entry_id = None
        self.__handle_data_changed()
        self.__fill_entry_view()

    def __handle_duplicate_callback(self):
        new_entry = entry_components.duplicate_entry(self.root_gui, self.selected_entry_id)
        self.selected_entry_id = new_entry.unique_id
        self.__handle_data_changed()
        self.__fill_entry_view()
