from collections import OrderedDict
from typing import Dict

from indexed import IndexedOrderedDict

from data.categories import Category
from data.entries import Entry
from data.tags import Tag


class SerializationData:
    def __init__(self, credentials: str, tags: Dict[str, Tag], characters: IndexedOrderedDict, categories: OrderedDict, history: list, history_index: int, entries: Dict[str, Entry]):
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

        characters_tmp = data["characters"]
        characters = IndexedOrderedDict()
        for k, v in characters_tmp.items():
            characters[k] = v

        categories_tmp = dict(map(lambda v: (v[0], Category.from_json(v[1])), data["categories"].items()))
        categories = OrderedDict()
        for k, v, in categories_tmp.items():
            categories[k] = v

        entries = dict(map(lambda v: (v[0], Entry.from_json(v[1])), data["entries"].items()))
        return cls(data["credentials"], tags, characters, categories, data["history"], data["history_index"], entries)
