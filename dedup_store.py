"""Track processed Gmail message IDs to prevent duplicate writes."""

from json_store import load_json, save_json

DEFAULT_PATH = "processed.json"


def load(path: str = DEFAULT_PATH) -> set:
    """Load processed message IDs. Returns empty set if missing."""
    return set(load_json(path, default_factory=list))


def save(ids: set, path: str = DEFAULT_PATH) -> None:
    """Write processed message IDs to disk."""
    save_json(sorted(ids), path)


def is_processed(ids: set, msg_id: str) -> bool:
    """Check if a message ID has already been processed."""
    return msg_id in ids


def mark_processed(ids: set, msg_id: str) -> None:
    """Add a message ID and save."""
    ids.add(msg_id)
    save(ids)
