from functools import partial
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFormLayout, QCheckBox, QLabel, QLineEdit, QPlainTextEdit, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QComboBox

from new.data import Entry, Category, Character, Output
from new.ui.desktop import gui_actions
from new.ui.desktop.spelling_widgets import SpellTextEdit, SpellTextEditSingleLine

if TYPE_CHECKING:
    from new.main import LitRPGToolsEngine
    from new.ui.desktop.gui import LitRPGToolsDesktopGUI


def create_entry_form(target_layout: QFormLayout, character: Character | None, category: Category, entry: Entry | None, history_index: int, header=True, readonly=False) -> list:
    # Add our header info
    if header:
        target_layout.addRow("Character:", QLabel(character.name))
        target_layout.addRow("Category:", QLabel(category.name))
        target_layout.addRow("History Index:", QLabel(str(history_index)))
        target_layout.addRow("", QLabel())

    # Add our contents
    callback_for_editables = []
    for index, (key, large_input) in enumerate(category.contents.items()):
        try:
            data = entry.data[index]
        except:
            data = ""

        # Kind of field
        if large_input:
            input_field = SpellTextEdit(data)
        else:
            input_field = SpellTextEditSingleLine(data)

        # Ensure the field is not editable
        if readonly:
            input_field.setReadOnly(True)

        target_layout.addRow(key, input_field)
        callback_for_editables.append(input_field)

    # Add display for 'disabled'
    check_box = QCheckBox()
    if entry is not None:
        check_box.setChecked(entry.is_disabled)
    if readonly:
        check_box.setEnabled(False)
    target_layout.addRow("Is Disabled?", check_box)
    callback_for_editables.append(check_box)
    return callback_for_editables


def create_entry_form_with_controls(target_layout, engine: 'LitRPGToolsEngine', parent: 'LitRPGToolsDesktopGUI', entry: Entry):
    character = engine.get_character_by_id(entry.character_id)
    category = engine.get_category_by_id(entry.category_id)
    entry_index = engine.get_entry_index_in_history(entry.unique_id)

    # Form
    entry_form = QWidget()
    entry_form_layout = QFormLayout()
    create_entry_form(entry_form_layout, character, category, entry, entry_index)
    entry_form.setLayout(entry_form_layout)

    # Controls
    entry_controls = QWidget()
    entry_controls_layout = QVBoxLayout()
    set_as_head_button = QPushButton("Set as Current Entry in History")
    set_as_head_button.clicked.connect(partial(gui_actions.set_entry_as_head, engine, parent, entry))
    entry_controls_layout.addWidget(set_as_head_button)
    set_as_selected_button = QPushButton("Highlight all entries in series.")
    set_as_selected_button.clicked.connect(partial(parent.set_curently_selected(entry_index)))
    entry_controls_layout.addWidget(set_as_selected_button)
    entry_edit_button = QPushButton("Edit")
    entry_edit_button.clicked.connect(partial(gui_actions.add_or_edit_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_edit_button)
    entry_update_button = QPushButton("Update")
    entry_update_button.clicked.connect(partial(gui_actions.update_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_update_button)
    entry_series_delete_button = QPushButton("Delete Series")
    entry_series_delete_button.clicked.connect(partial(gui_actions.delete_entry_series, engine, parent, entry))
    entry_controls_layout.addWidget(entry_series_delete_button)
    entry_delete_button = QPushButton("Delete")
    entry_delete_button.clicked.connect(partial(gui_actions.delete_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_delete_button)
    entry_duplicate_button = QPushButton("Duplicate")
    entry_duplicate_button.clicked.connect(partial(gui_actions.duplicate_entry, engine, parent, entry))
    entry_controls_layout.addWidget(entry_duplicate_button)
    entry_view_button = QPushButton("Add to View")
    entry_view_button.clicked.connect(partial(gui_actions.add_entry_to_output, engine, parent, entry))
    entry_controls_layout.addWidget(entry_view_button)
    spacer = QWidget()
    entry_controls_layout.addWidget(spacer)
    entry_controls_layout.setStretchFactor(spacer, 100)
    entry_controls_layout.setContentsMargins(0, 0, 0, 0)
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
    target_layout.addWidget(entry_widget)


def create_category_form(target_layout, category: Category):
    # Add our header info
    target_layout.addRow("Category:", QLabel(category.name))
    target_layout.addRow("", QLabel())

    # Add our contents
    target_layout.addRow("Property Text", QLabel("Requires Large Input"))
    for index, (key, large_input) in enumerate(category.contents.items()):
        check_box = QCheckBox()
        check_box.setChecked(large_input)
        check_box.setEnabled(False)
        target_layout.addRow(key, check_box)

    # Update strings
    target_layout.addRow("Creation text:", QLabel(category.creation_text))
    target_layout.addRow("Update text:", QLabel(category.update_text))

    # Add configs
    print_to_overview_check_box = QCheckBox()
    print_to_overview_check_box.setChecked(category.print_to_character_overview)
    print_to_overview_check_box.setEnabled(False)
    target_layout.addRow("Print to Overview Disabled?", print_to_overview_check_box)

    can_update_check_box = QCheckBox()
    can_update_check_box.setChecked(category.can_update)
    can_update_check_box.setEnabled(False)
    target_layout.addRow("Can Update?", can_update_check_box)

    is_singleton_check_box = QCheckBox()
    is_singleton_check_box.setChecked(category.single_entry_only)
    is_singleton_check_box.setEnabled(False)
    target_layout.addRow("Is singleton?", is_singleton_check_box)


def create_output_form(target_layout, output: Output, history_indices: list):
    # Name field
    unique_name_field = QLineEdit(output.name)
    unique_name_field.setReadOnly(True)
    target_layout.addRow("Unique Name:", unique_name_field)

    # Early boundary
    output_from_field = QLineEdit(str(output.from_index))
    output_from_field.setReadOnly(True)
    target_layout.addRow("Output History From:", output_from_field)

    # Late boundary
    output_to_field = QLineEdit(str(output.to_index))
    output_to_field.setReadOnly(True)
    target_layout.addRow("Output History To (Inclusive):", output_to_field)

    # Gsheets target
    target_gsheet_field = QComboBox(output.gsheet_target)
    target_gsheet_field.setReadOnly(True)
    target_layout.addRow("Target GSheet:", target_gsheet_field)

    # History Index Members
    members_field = QPlainTextEdit("\n".join(history_indices))
    members_field.setReadOnly(True)
    target_layout.addRow("Current Members (Index in History):", members_field)
