from PyQt6.QtWidgets import QDialog, QFormLayout, QPushButton, QComboBox, QLineEdit, QLabel, QCheckBox

from new.ui.desktop.spelling_widgets import SpellTextEdit, SpellTextEditSingleLine


class CreateEntryDialog(QDialog):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.data = list()

        # Form Content
        self.character_selector = QComboBox()
        self.character_selector.addItems(self.engine.get_characters().keys())
        self.character_selector.currentTextChanged.connect(self.character_changed)
        self.category_selector = QComboBox()
        self.categories = dict()
        self.category_selector.currentTextChanged.connect(self.category_changed)
        self.print_to_overview = None
        self.print_to_history = None
        self.done_button = None

        # Form Layout
        self.form_layout = QFormLayout()
        self.form_layout.addRow("Character:", self.character_selector)
        self.form_layout.addRow("Category:", self.category_selector)
        self.setLayout(self.form_layout)
        self.setMinimumWidth(640)

        self.current_category = None
        self.character_changed()
        self.viable = False

    def character_changed(self):
        character = self.character_selector.currentText()
        if character is None or character == "":
            return

        all_categories = self.engine.get_character_categories(character)
        if len(all_categories) == 0:
            return

        categories = dict()
        for category_name in all_categories:
            category = self.engine.get_category(category_name)
            if category.is_singleton:
                view = self.engine.get_category_state_for_entity(category_name, self.character_selector.currentIndex())
                if view is not None and len(view) != 0:
                    continue

            categories[category_name] = category
        self.categories = categories
        self.category_selector.blockSignals(True)
        self.category_selector.clear()
        self.category_selector.addItems(categories)
        self.category_selector.blockSignals(False)
        self.category_changed()

    def category_changed(self, *args):
        # Delete old rows
        self.data.clear()
        for row in range(2, self.form_layout.rowCount()):
            self.form_layout.removeRow(2)

        # Add in the new data
        current_item = self.category_selector.currentText()
        self.current_category = self.categories[current_item]
        for property in self.current_category.get_properties():
            name = property.get_property_name()
            if name != "":
                if property.requires_large_input():
                    item = SpellTextEdit("")
                else:
                    item = SpellTextEditSingleLine("")

                self.data.append(item)
                self.form_layout.addRow(name, item)
            else:
                self.data.append(None)

        self.print_to_overview = QCheckBox()
        if self.current_category.print_to_overview:
            self.print_to_overview.setChecked(True)
        else:
            self.print_to_overview.setChecked(False)
            self.print_to_overview.setEnabled(False)
        self.form_layout.addRow("Print to overview:", self.print_to_overview)

        self.print_to_history = QCheckBox()
        if self.current_category.print_to_history:
            self.print_to_history.setChecked(True)
        else:
            self.print_to_history.setChecked(False)
            self.print_to_history.setEnabled(False)
        self.form_layout.addRow("Print to history:", self.print_to_history)

        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)
        self.form_layout.addRow("", self.done_button)

    def get_data(self):
        data_out = list()
        for item in self.data:
            if item is None:
                data_out.append("")
            elif isinstance(item, QLineEdit):
                data_out.append(item.text())
            else:
                data_out.append(item.toPlainText())
        return data_out

    def handle_done(self, *args):
        self.viable = True
        self.close()


class EditEntryDialog(QDialog):
    def __init__(self, category, data, print_to_overview, print_to_history):
        super().__init__()
        self.category = category
        self.data_values = data
        self.data = list()

        # Form Content
        self.print_to_overview = QCheckBox()
        self.print_to_overview.setChecked(print_to_overview)
        self.print_to_overview.setEnabled(self.category.print_to_overview)
        self.print_to_history = QCheckBox()
        self.print_to_history.setChecked(print_to_history)
        self.print_to_history.setEnabled(self.category.print_to_history)
        self.done_button = QPushButton("Done")
        self.done_button.clicked.connect(self.handle_done)

        # Form Layout
        self.form_layout = QFormLayout()
        self.form_layout.addRow("Category:", QLabel(category.get_name()))
        props = category.get_properties()
        for row_index in range(len(props)):
            prop_name = props[row_index].get_property_name()
            if prop_name != "":
                try:
                    value = self.data_values[row_index]
                except:
                    self.data_values.append("")
                    value = ""

                if props[row_index].requires_large_input():
                    item = SpellTextEdit(value)
                else:
                    item = QLineEdit(value)

                self.data.append(item)
                self.form_layout.addRow(prop_name, item)
            else:
                self.data.append(None)
        self.form_layout.addRow("Print to overview:", self.print_to_overview)
        self.form_layout.addRow("Print to history:", self.print_to_history)
        self.form_layout.addRow("", self.done_button)
        self.setLayout(self.form_layout)

        self.viable = False

    def get_data(self):
        data_out = list()
        for item in self.data:
            if item is None:
                data_out.append("")
            elif isinstance(item, QLineEdit):
                data_out.append(item.text())
            else:
                data_out.append(item.toPlainText())
        return data_out

    def handle_done(self, *args):
        self.viable = True
        self.close()


