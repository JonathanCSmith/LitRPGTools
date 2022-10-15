import uuid


class Entry:
    def __init__(self, category, values, unique_key=None, parent_key=None, print_to_overview=True, character=0, print_to_history=True):
        if unique_key is None:
            uuid_val = uuid.uuid4()
            unique_key = str(uuid_val)

        self.unique_key = unique_key
        self.character = character
        self.category = category
        self.values = values
        self.parent_key = parent_key
        self.print_to_overview = print_to_overview
        self.print_to_history = print_to_history

    def get_unique_key(self):
        return self.unique_key

    def get_category(self):
        return self.category

    def get_values(self):
        return self.values

    def set_values(self, values: list):
        self.values = values

    def get_parent_key(self):
        return self.parent_key

    def get_print_to_overview(self):
        return self.print_to_overview

    def set_print_to_overview(self, value):
        self.print_to_overview = value

    @classmethod
    def from_json(cls, data):
        return cls(**data)
