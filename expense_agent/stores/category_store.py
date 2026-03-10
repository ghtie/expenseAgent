"""Local category lookup backed by a JSON file."""

from expense_agent.stores.json_store import load_json, save_json
from expense_agent.utils.lookup_utils import longest_substring_match

DEFAULT_PATH = "categories.json"


def load(path: str = DEFAULT_PATH) -> dict:
    """Read the JSON file and return the mapping. Returns {} if missing."""
    return load_json(path)


def save(mapping: dict, path: str = DEFAULT_PATH) -> None:
    """Write the mapping dict back to disk."""
    save_json(mapping, path)


def lookup(mapping: dict, item: str) -> str | None:
    """
    Look up category for an item. Tries exact match first, then
    fuzzy substring matching (longest match wins to avoid false positives).
    """
    lower = item.lower()

    # Exact match (case-insensitive)
    for key, category in mapping.items():
        if key.lower() == lower:
            return category

    # Fuzzy: bidirectional so "Trader Joes" matches item "Trader Joe" and vice versa
    best_key = longest_substring_match(lower, mapping, bidirectional=True)
    return mapping[best_key] if best_key else None
