import json
import os.path
from collections import OrderedDict
from pathlib import Path

from indexed import IndexedOrderedDict

from data.models import DataFile, Category, Character, Entry, Output


def load_json(file_path):
    if not os.path.isfile(file_path):
        raise NotADirectoryError()

    with open(file_path, "r") as source_file:
        return json.load(source_file)


def save_json(file_path, data_holder):
    jsons = json.dumps(data_holder, default=lambda o: o.__dict__, indent=4)

    # Ensure our folders exist
    folders = os.path.dirname(os.path.abspath(file_path))
    Path(folders).mkdir(parents=True, exist_ok=True)

    # Serialize
    with open(file_path, 'w') as output_file:
        output_file.write(jsons)


def handle_old_save_file_loader(json_data) -> DataFile | None:
    attempt_count = 0
    try:
        # Unpack categories
        category_map = dict()
        categories = IndexedOrderedDict()
        for n, v in json_data["categories"].items():
            contents = IndexedOrderedDict()
            for entry in v["properties"]:
                contents[entry["property_name"]] = entry["requires_large_input_box"]

            category = Category(
                name=v["name"],
                contents=contents,
                creation_text=v["new_history_entry"],
                update_text=v["update_history_entry"],
                print_to_character_overview=v["print_to_overview"],
                can_update=v["can_change_over_time"],
                single_entry_only=v["is_singleton"]
            )
            categories[category.unique_id] = category
            category_map[category.name] = category.unique_id

        # Unpack characters
        character_map = dict()
        characters = IndexedOrderedDict()
        for index, (n, v) in enumerate(json_data["characters"].items()):
            # Custom remap categories
            character_categories = list()
            for category_name in v:
                character_categories.append(category_map[category_name])

            character = Character(n, character_categories)
            characters[character.unique_id] = character
            character_map[index] = character.unique_id

        # Unpack entries
        entries = dict()
        entries_not_in_output = list()
        for k, v in json_data["entries"].items():
            entry = Entry(
                character_id=character_map[v["character"]],
                category_id=category_map[v["category"]],
                data=v["values"],
                is_disabled=v["print_to_overview"],
                unique_id=v["unique_key"],
                parent_id=v["parent_key"]
            )

            # Exclude these entries from any outputs we create
            if not v["print_to_history"]:
                entries_not_in_output.append(entry.unique_id)

            # Save it
            entries[entry.unique_id] = entry

        # Fix child keys
        for entry in entries.values():
            if entry.parent_id is not None:
                parent_entry = entries[entry.parent_id]
                parent_entry.child_id = entry.unique_id

        # Unpack outputs - this is difficult
        history = json_data["history"]
        outputs = OrderedDict()
        for k, v in json_data["tags"].items():
            output = Output(
                name=v["tag_name"],
                gsheet_target=v["tag_target"],
                target_entry_id=v["tagged_entry_key"],
                members=list(),
                ignored=list()
            )
            outputs[output.unique_id] = output

        data_holder = DataFile(
            characters=characters,
            categories=categories,
            history=history,
            entries=entries,
            outputs=outputs,
            gsheets_credentials_path=json_data["credentials"],
            history_index=json_data["history_index"],
            file_version="1.9.0"
        )
        return data_holder

    except Exception as e:
        attempt_count += 1
