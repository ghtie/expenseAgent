"""Track processed Gmail message IDs to prevent duplicate writes."""

import json
import os

DEFAULT_PATH = "processed.json"


def load(path: str = DEFAULT_PATH) -> set:
    """Load processed message IDs. Returns empty set if missing."""
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(json.load(f))


def save(ids: set, path: str = DEFAULT_PATH) -> None:
    """Write processed message IDs to disk."""
    with open(path, "w") as f:
        json.dump(sorted(ids), f, indent=2)
        f.write("\n")


def is_processed(ids: set, msg_id: str) -> bool:
    """Check if a message ID has already been processed."""
    return msg_id in ids


def mark_processed(ids: set, msg_id: str) -> None:
    """Add a message ID and save."""
    ids.add(msg_id)
    save(ids)
