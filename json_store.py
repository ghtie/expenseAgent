"""Shared JSON load/save helpers for the store modules."""

import json
import os


def load_json(path: str, default_factory=dict):
    """Read a JSON file. Returns default_factory() if missing."""
    if not os.path.exists(path):
        return default_factory()
    with open(path) as f:
        return json.load(f)


def save_json(data, path: str) -> None:
    """Write data to a JSON file with indent=2 and trailing newline."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
