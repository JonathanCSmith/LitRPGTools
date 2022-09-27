from typing import Dict

from data.categories import Category
from data.entries import Entry
from data.tags import Tag


class SerializationData:
    def __init__(self, credentials: str, tags: Dict[str, Tag], characters: list, categories: Dict[str, Category], history: list, history_index: int, entries: Dict[str, Entry]):
        self.credentials = credentials
        self.tags = tags
        self.characters = characters
        self.categories = categories
        self.history = history
        self.history_index = history_index
        self.entries = entries

    @classmethod
    def from_json(cls, data):
        tags = dict(map(lambda v: (v[0], Tag.from_json(v[1])), data["tags"].items()))
        categories = dict(map(lambda v: (v[0], Category.from_json(v[1])), data["categories"].items()))
        entries = dict(map(lambda v: (v[0], Entry.from_json(v[1])), data["entries"].items()))
        return cls(data["credentials"], tags, data["characters"], categories, data["history"], data["history_index"], entries)
