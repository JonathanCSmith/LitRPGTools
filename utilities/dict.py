from indexed import IndexedOrderedDict


def move_item_in_indexedordererdict_by(iod: IndexedOrderedDict, key, shift) -> IndexedOrderedDict | None:
    if key not in iod:
        return None

    # Cache our keys and our current index location
    key_list = list(iod.keys())
    current_index = key_list.index(key)

    # Check if our move is valid and bail if not
    if current_index + shift < 0 or current_index + shift >= len(iod):
        return None

    # Move
    key_list.insert(current_index + shift, key_list.pop(current_index))

    # Remake our dictionary according to our new list of ordered keys
    ordered = IndexedOrderedDict()
    for key in key_list:
        ordered[key] = iod[key]

    # Return reordered dict
    return ordered


def move_item_in_iod_by_index_to_position(iod: IndexedOrderedDict, source_index: int, target_index: int) -> IndexedOrderedDict:
    # Cache our keys as a list
    key_list = list(iod.keys())
    key_list = move_item_in_list_by_index_to_position(key_list, source_index, target_index)

    # Remake our dictionary according to our new list of ordered keys
    ordered = IndexedOrderedDict()
    for key in key_list:
        ordered[key] = iod[key]

    # Return reordered dict
    return ordered


def move_item_in_list_by_index_to_position(l: list, source_index: int, target_index: int) -> list:
    l.insert(target_index, l.pop(source_index))
    return l


