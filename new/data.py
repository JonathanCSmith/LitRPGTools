import uuid
from typing import List, Dict, Tuple, Any

from indexed import IndexedOrderedDict


class Data:
    def __init__(self, unique_id: str = None):
        # Allow us to automate uuid generation
        if unique_id is None:
            self.unique_id = str(uuid.uuid4())
        else:
            self.unique_id = unique_id


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
            dynamic_data_initialisations: Dict[str, Any] = None,
            dynamic_data_operations: Dict[str, Tuple[str, str]] = None,
            unique_id: str = None):
        super(Category, self).__init__(unique_id)

        self.name = name
        self.contents = contents
        self.creation_text = creation_text
        self.update_text = update_text
        self.print_to_character_overview = print_to_character_overview
        self.can_update = can_update
        self.single_entry_only = single_entry_only
        if dynamic_data_initialisations is None:
            dynamic_data_initialisations: Dict[str, Any] = dict()
        self.dynamic_data_initialisations = dynamic_data_initialisations
        if dynamic_data_operations is None:
            dynamic_data_operations: Dict[str, Tuple[str, str]] = dict()
        self.dynamic_data_operations: Dict[str, Tuple[str, str]] = dynamic_data_operations


class Output(Data):
    def __init__(self, name: str, gsheet_target: str, members: List[str], ignored: List[str], unique_id: str = None):
        super(Output, self).__init__(unique_id)
        self.name = name
        self.gsheet_target = gsheet_target
        self.members = members
        self.ignored = ignored


class Entry(Data):
    def __init__(
            self,
            character_id: str,
            category_id: str,
            data: list,
            is_disabled: bool = False,
            dynamic_data_initialisations: Dict[str, Any] = None,
            dynamic_data_operations: Dict[str, Tuple[str, str]] = None,
            unique_id: str = None,
            parent_id: str = None,
            child_id: str = None,
            output_id: str = None):
        super(Entry, self).__init__(unique_id)
        self.character_id = character_id
        self.category_id = category_id
        self.data = data
        self.is_disabled = is_disabled
        self.parent_id = parent_id
        self.child_id = child_id
        self.output_id = output_id
        if dynamic_data_initialisations is None:
            dynamic_data_initialisations: Dict[str, Any] = dict()
        self.dynamic_data_initialisations = dynamic_data_initialisations
        if dynamic_data_operations is None:
            dynamic_data_operations: Dict[str, Tuple[str, str]] = dict()
        self.dynamic_data_operations: Dict[str, Tuple[str, str]] = dynamic_data_operations
