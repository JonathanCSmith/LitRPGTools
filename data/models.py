import uuid
from collections import OrderedDict
from typing import List, Dict, Tuple, Any

from indexed import IndexedOrderedDict

FILE_VERSION = "2.0.1"


class Data:
    def __init__(self, unique_id: str = None):
        # Allow us to automate uuid generation
        if unique_id is None:
            self.unique_id = str(uuid.uuid4())
        else:
            self.unique_id = unique_id

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)


class Character(Data):
    def __init__(self, name: str, categories: list = None, unique_id: str = None):
        super(Character, self).__init__(unique_id)
        self.name = name

        # Fill in categories with empty list if its forgotten
        if categories is None:
            self.categories = list()
        else:
            self.categories = categories


class Category(Data):
    def __init__(
            self,
            name: str,
            contents: IndexedOrderedDict,
            creation_text: str = None,
            update_text: str = None,
            print_to_character_overview: bool = False,
            can_update: bool = False,
            single_entry_only: bool = False,
            dynamic_data_operations: Dict[str, Tuple[str, str, str]] = None,
            dynamic_data_operation_templates: Dict[str, Tuple[str, str, str]] = None,
            unique_id: str = None):
        super(Category, self).__init__(unique_id)

        self.name = name
        self.contents = contents
        self.creation_text = creation_text
        self.update_text = update_text
        self.print_to_character_overview = print_to_character_overview
        self.can_update = can_update
        self.single_entry_only = single_entry_only
        if dynamic_data_operations is None:
            dynamic_data_operations: Dict[str, Tuple[str, str, str]] = dict()
        self.dynamic_data_operations: Dict[str, Tuple[str, str, str]] = dynamic_data_operations
        if dynamic_data_operation_templates is None:
            dynamic_data_operation_templates: Dict[str, Tuple[str, str, str]] = dict()
        self.dynamic_data_operation_templates: Dict[str, Tuple[str, str, str]] = dynamic_data_operation_templates


class Output(Data):
    def __init__(self, name: str, gsheet_target: str, target_entry_id: str, members: List[str], ignored: List[str], unique_id: str = None):
        super(Output, self).__init__(unique_id)
        self.name = name
        self.gsheet_target = gsheet_target
        self.target_entry_id = target_entry_id
        self.members = members
        self.ignored = ignored


class Entry(Data):
    def __init__(
            self,
            character_id: str,
            category_id: str,
            data: list,
            is_disabled: bool = False,
            dynamic_data_operations: Dict[str, Tuple[str, str, str]] = None,
            unique_id: str = None,
            parent_id: str = None,
            child_id: str = None):
        super(Entry, self).__init__(unique_id)
        self.character_id = character_id
        self.category_id = category_id
        self.data = data
        self.is_disabled = is_disabled
        self.parent_id = parent_id
        self.child_id = child_id
        if dynamic_data_operations is None:
            dynamic_data_operations: Dict[str, Tuple[str, str, str]] = dict()
        self.dynamic_data_operations: Dict[str, Tuple[str, str, str]] = dynamic_data_operations


class DataFile:
    def __init__(
            self,
            characters: Dict[str, Character],
            categories: Dict[str, Category],
            history: List[str],
            entries: Dict[str, Entry],
            outputs: Dict[str, Output],
            gsheets_credentials_path: str,
            history_index: int,
            file_version: str = FILE_VERSION):
        self.file_version = file_version
        self.gsheets_credentials_path = gsheets_credentials_path
        self.history_index = history_index
        self.history = history
        self.characters = characters
        self.categories = categories
        self.entries = entries
        self.outputs = outputs

    @classmethod
    def from_json(cls, json_data):
        # Old data handling
        if json_data["file_version"] != FILE_VERSION:
            json_data = DataFile.__convert_old_data(json_data)

        characters = IndexedOrderedDict()
        for k, v in json_data["characters"].items():
            character = Character.from_json(v)
            characters[k] = character

        categories = IndexedOrderedDict()
        for k, v in json_data["categories"].items():
            category = Category.from_json(v)
            categories[k] = category

        entries = dict()
        for k, v in json_data["entries"].items():
            entry = Entry.from_json(v)
            entries[k] = entry

        outputs = OrderedDict()
        for k, v in json_data["outputs"].items():
            output = Output.from_json(v)
            outputs[k] = output

        return cls(
            characters=characters,
            categories=categories,
            history=json_data["history"],
            entries=entries,
            outputs=outputs,
            gsheets_credentials_path=json_data["gsheets_credentials_path"],
            history_index=json_data["history_index"])

    @classmethod
    def __convert_old_data(cls, json_data):
        # Introduction of multiple scopes for dynamic data
        if json_data["file_version"] == "2.0.0":
            for category in json_data["categories"].values():
                for dynamic_data_key in category["dynamic_data_operations"]:
                    if category["dynamic_data_operations"][dynamic_data_key][1]:
                        category["dynamic_data_operations"][dynamic_data_key][1] = "FUNCTION"

                    else:
                        category["dynamic_data_operations"][dynamic_data_key][1] = "INSTANT"

                for dynamic_data_key in category["dynamic_data_operation_templates"]:
                    if category["dynamic_data_operation_templates"][dynamic_data_key][1]:
                        category["dynamic_data_operation_templates"][dynamic_data_key][1] = "FUNCTION"

                    else:
                        category["dynamic_data_operation_templates"][dynamic_data_key][1] = "INSTANT"
            for entry in json_data["entries"].values():
                for dynamic_data_key in entry["dynamic_data_operations"]:
                    if entry["dynamic_data_operations"][dynamic_data_key][1]:
                        entry["dynamic_data_operations"][dynamic_data_key][1] = "FUNCTION"

                    else:
                        entry["dynamic_data_operations"][dynamic_data_key][1] = "INSTANT"

        return json_data

