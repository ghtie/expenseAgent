"""Local category lookup backed by a JSON file."""

import json
import os

DEFAULT_PATH = "categories.json"


def load(path: str = DEFAULT_PATH) -> dict:
    """Read the JSON file and return the mapping. Returns {} if missing."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save(mapping: dict, path: str = DEFAULT_PATH) -> None:
    """Write the mapping dict back to disk."""
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        f.write("\n")



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

    # Fuzzy: find the longest stored key that appears in the item or vice versa
    best_key = None
    best_len = 0
    for key in mapping:
        key_lower = key.lower()
        if len(key_lower) < 3:
            continue  # skip very short keys to avoid false matches
        if key_lower in lower or lower in key_lower:
            if len(key_lower) > best_len:
                best_key = key
                best_len = len(key_lower)

    return mapping[best_key] if best_key else None
