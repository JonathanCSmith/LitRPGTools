class Tag:
    def __init__(self, tag_name, tagged_entry_key, tag_target, tag_pointers=None):
        self.tag_name = tag_name
        self.tagged_entry_key = tagged_entry_key
        self.tag_target = tag_target
        if tag_pointers is None:
            self.tag_pointers = dict()
        else:
            self.tag_pointers = tag_pointers

    def get_name(self):
        return self.tag_name

    def get_associated_entry_key(self):
        return self.tagged_entry_key

    def get_tag_target(self):
        return self.tag_target

    def get_tag_pointers(self):
        return self.tag_pointers

    @classmethod
    def from_json(cls, data):
        return cls(**data)

