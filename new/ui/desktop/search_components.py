from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QFormLayout, QPushButton, QHBoxLayout, QListWidget, QAbstractItemView, QLineEdit, QCheckBox, QListWidgetItem

from new.data import Entry, Category, Character
from new.ui.desktop import entry_components
from new.ui.desktop.category_components import create_category_form, add_or_edit_category, delete_category
from new.ui.desktop.custom_generic_components import VisibleDynamicSplitPanel

if TYPE_CHECKING:
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI
    from new.main import LitRPGToolsEngine


class SearchTab(VisibleDynamicSplitPanel):
    def __init__(self, parent: 'LitRPGToolsDesktopGUI', engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Currently selected
        self.results = list()

        # Main components
        self._sidebar_widget = SearchSidebar(self, engine)
        self._view_widget = SearchView(self, engine)

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

    def set_results(self, results: list):
        self.results = results

    def _selection_changed(self, index: int):
        self.current_selection = self.results[index]
        self._view_widget.draw()


class SearchSidebar(QWidget):
    def __init__(self, parent: SearchTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Actual display of what we wanted to display (as per above).
        self.__active_list = QListWidget()
        self.__active_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.__active_list.itemSelectionChanged.connect(self.__handle_sidebar_selection_changed_callback)

        # Search terms
        self.__search_bar = QLineEdit()
        self.__replace_bar = QLineEdit()
        self.__search_button = QPushButton("Search")
        self.__search_button.clicked.connect(self.__handle_search_callback)
        self.__replace_button = QPushButton("Replace Next")
        self.__replace_button.clicked.connect(self.__handle_replace_single_callback)
        self.__replace_all_button = QPushButton("Replace All")
        self.__replace_all_button.clicked.connect(self.__handle_replace_all_callback)

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
        self.setLayout(self.__layout)
        self.setContentsMargins(0, 0, 0, 0)

    def __handle_sidebar_selection_changed_callback(self):
        self._parent._selection_changed(self.__active_list.currentRow())

    def __handle_search_callback(self):
        # Get our search data
        search_text = self.__search_bar.text()
        if search_text is None or search_text == "":
            return

        # Get the results
        results = self._engine.search_all(search_text)
        self._parent.set_results(results)

        # Block signals and clear list
        self.__active_list.blockSignals(True)
        self.__active_list.clear()

        # Loop through our entries and add them
        for index, result in enumerate(results):
            if isinstance(result, Entry):
                category = self._engine.get_category_by_id(result.category_id)
                character = self._engine.get_character_by_id(result.character_id)

                # Display string format
                if result.parent_id is None:
                    display_string = category.creation_text
                else:
                    display_string = category.update_text
                display_string = self.__fill_entry_display_string(display_string, index, character, category, result)

            elif isinstance(result, Category):
                display_string = self.__fill_category_display_string(result)

            else:
                continue

            # Add the string
            item = QListWidgetItem(display_string)
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.__active_list.addItem(item)

        # Return signals
        self.__active_list.blockSignals(False)

    def __fill_entry_display_string(self, template_string: str, index: int, character: Character, category: Category, entry: Entry):
        string_result = template_string.format(*entry.data)  # TODO! Codify some nice stuff here
        return "[" + str(index) + "] (" + character.name + "): " + string_result

    def __fill_category_display_string(self, category: Category):
        return "[Category]: " + category.name

    def __handle_replace_single_callback(self):
        pass

    def __handle_replace_all_callback(self):
        pass

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
        self.__handle_search_callback()

    def get_should_display_dynamic(self):
        return self.__view_dynamic

    def get_currently_selected(self):
        return self.__active_list.currentItem()

    def set_currently_selected(self, index):
        self.__active_list.setCurrentRow(index)


class SearchView(QScrollArea):
    def __init__(self, parent: SearchTab, engine: 'LitRPGToolsEngine'):
        super().__init__()
        self._parent = parent
        self._engine = engine

        # Main
        self.__results_view = QWidget()
        self.__results_view.setStyleSheet("#bordered { border:1px solid rgb(0, 0, 0); }")
        self.__results_view_layout = QVBoxLayout()
        self.__results_view_layout.setContentsMargins(0, 0, 0, 0)
        self.__results_view.setLayout(self.__results_view_layout)
        self.setWidget(self.__results_view)
        self.setWidgetResizable(True)
        self.setContentsMargins(0, 0, 0, 0)

    def draw(self):
        # Clear our current data
        result = self.__results_view_layout.itemAt(0)
        if result is not None:
            result_widget = result.widget()
            result_widget.deleteLater()

        # Retrieve our selection
        item = self._parent.get_current_selection()
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        result = self._parent.results[index]

        # Draw the result
        if isinstance(result, Entry):
            self.__draw_entry(result)

        elif isinstance(result, Category):
            self.__draw_category(result)

    def __draw_entry(self, entry: Entry):
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
        entry_components.create_entry_form(self._engine, entry_form_layout, character, category, entry, current_index, header=True, readonly=True, translate_with_dynamic_data=should_display_dynamic_data, dynamic_data_index=target_index)
        entry_form.setLayout(entry_form_layout)

        # Controls
        entry_controls = QWidget()
        entry_controls_layout = QVBoxLayout()
        set_as_head_button = QPushButton("Set as Current Entry in History")
        set_as_head_button.clicked.connect(partial(self.__handle_set_as_head_callback, entry))
        entry_controls_layout.addWidget(set_as_head_button)
        entry_edit_button = QPushButton("Edit")
        entry_edit_button.clicked.connect(partial(self.__handle_edit_callback, entry))
        entry_controls_layout.addWidget(entry_edit_button)
        entry_update_button = QPushButton("Update")
        entry_update_button.clicked.connect(partial(self.__handle_update_callback, entry))
        entry_controls_layout.addWidget(entry_update_button)
        entry_series_delete_button = QPushButton("Delete Series")
        entry_series_delete_button.clicked.connect(partial(self.__handle_delete_series_callback, entry))
        entry_controls_layout.addWidget(entry_series_delete_button)
        entry_delete_button = QPushButton("Delete")
        entry_delete_button.clicked.connect(partial(self.__handle_delete_callback, entry))
        entry_controls_layout.addWidget(entry_delete_button)
        entry_duplicate_button = QPushButton("Duplicate")
        entry_duplicate_button.clicked.connect(partial(self.__handle_duplicate_callback, entry))
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

    def __draw_category(self, category: Category):
        # Form
        category_form = QWidget()
        category_form_layout = QFormLayout()
        create_category_form(category_form_layout, category)
        category_form.setLayout(category_form_layout)

        # Controls
        category_controls = QWidget()
        category_controls_layout = QVBoxLayout()
        category_edit_button = QPushButton("Edit")
        category_edit_button.clicked.connect(partial(add_or_edit_category, self._engine, self._parent, category))
        category_controls_layout.addWidget(category_edit_button)
        category_delete_button = QPushButton("Delete")
        category_delete_button.clicked.connect(partial(delete_category, self._engine, self._parent, category))
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

    def __handle_set_as_head_callback(self, entry: Entry):
        entry_components.set_entry_as_head(self._engine, entry)

    def __handle_edit_callback(self, entry: Entry):
        entry_components.edit_entry(self._engine, self, entry)
        self._parent.draw()

    def __handle_update_callback(self, entry: Entry):
        update = entry_components.update_entry(self._engine, self, entry)
        if update is not None:
            self._parent.set_curently_selected(self._engine.get_entry_index_in_history(update.unique_id))

    def __handle_delete_series_callback(self, entry: Entry):
        entry_components.delete_entry_series(self._engine, self, entry)
        self._parent.set_curently_selected(self._engine.get_current_history_index())

    def __handle_delete_callback(self, entry: Entry):
        entry_components.delete_entry(self._engine, self, entry)
        self._parent.set_curently_selected(self._engine.get_current_history_index())

    def __handle_duplicate_callback(self, entry: Entry):
        entry_components.duplicate_entry(self._engine, entry)
        self._parent.set_curently_selected(self._engine.get_current_history_index())
