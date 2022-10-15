class CategoryProperty:
    def __init__(self, property_name, requires_large_input_box):
        self.property_name = property_name
        self.requires_large_input_box = requires_large_input_box

    def get_property_name(self):
        return self.property_name

    def requires_large_input(self):
        return self.requires_large_input_box

    @classmethod
    def from_json(cls, data):
        return cls(**data)


class Category:
    def __init__(self, name, properties, new_history_entry, update_history_entry, print_to_overview=False, can_change_over_time=True, is_singleton=False, print_to_history=False):
        self.name = name
        self.properties = properties
        self.new_history_entry = new_history_entry
        self.update_history_entry = update_history_entry
        self.print_to_overview = print_to_overview
        self.print_to_history = print_to_history
        self.can_change_over_time = can_change_over_time
        self.is_singleton = is_singleton

    def get_name(self):
        return self.name

    def get_properties(self):
        return self.properties

    def get_new_history_entry(self):
        return self.new_history_entry

    def get_update_history_entry(self):
        return self.update_history_entry

    def get_print_to_overview(self):
        return self.print_to_overview

    @classmethod
    def from_json(cls, data):
        properties = list(map(CategoryProperty.from_json, data["properties"]))
        return cls(data["name"], properties, data["new_history_entry"], data["update_history_entry"], data["print_to_overview"], data["can_change_over_time"], data["is_singleton"], data["print_to_history"])
