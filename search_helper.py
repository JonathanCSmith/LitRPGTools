import math
import string

from data import Entry, Category


def tokenize_string(search_string: str) -> list | None:
    if search_string is None:
        return None

    # Remove punctuation
    search_string = search_string.translate(str.maketrans('', '', string.punctuation))

    # Lower case and split on whitespace
    return [item.lower() for item in search_string.split()]


def tokenize_entry(entry: Entry) -> list | None:
    if entry is None:
        return None

    # Go through relevant areas of entry and tokenize
    tokens = []
    for item in entry.data:
        tokens.extend(tokenize_string(item))

    return tokens


def tokenize_category(category: Category) -> list | None:
    if category is None:
        return None

    # Go through relevant data areas of category and tokenize
    tokens = []
    tokens.extend(tokenize_string(category.name))
    for item in category.contents:
        tokens.extend(tokenize_string(item))

    return tokens


def search_tokens(search_terms: list, target_document_contents: list) -> bool:
    if len(search_terms) == 0 or len(target_document_contents) == 0:
        return False

    # Reduce search space
    search_terms = set(search_terms)
    target_document_contents = set(target_document_contents)

    # Compare
    positive_count = 0
    for item in search_terms:
        for doc_token in target_document_contents:
            if doc_token.find(item) >= 0:
                positive_count += 1

    # Return true if our count is greater than half of the search terms
    return positive_count >= math.ceil(len(search_terms) / 2)

