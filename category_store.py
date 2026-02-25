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
    """Case-insensitive lookup for an item. Returns category or None."""
    lower = item.lower()
    for key, category in mapping.items():
        if key.lower() == lower:
            return category
    return None
