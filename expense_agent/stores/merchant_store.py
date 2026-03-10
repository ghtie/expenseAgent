"""Merchant auto-learn: maps raw merchant substrings to canonical name + category."""

from expense_agent.stores.json_store import load_json, save_json
from expense_agent.utils.lookup_utils import longest_substring_match
from expense_agent.utils.merchant_utils import normalize_merchant

DEFAULT_PATH = "merchants.json"


def load(path: str = DEFAULT_PATH) -> dict:
    """Read merchants.json. Returns {} if missing."""
    return load_json(path)


def save(mapping: dict, path: str = DEFAULT_PATH) -> None:
    """Write merchants.json to disk."""
    save_json(mapping, path)


def derive_key(raw_merchant: str) -> str:
    """
    Derive a stable lookup key from a raw merchant string.

    Lowercases, collapses whitespace, strips trailing store codes/numbers/
    location suffixes so the key generalizes across branches.
    E.g. "TRADER JOE S #123" -> "trader joe"
    """
    return normalize_merchant(raw_merchant)


def lookup(mapping: dict, raw_merchant: str) -> dict | None:
    """
    Case-insensitive substring match against raw merchant string.
    Returns {"name": "...", "category": "..."} or None.
    Longest match wins to avoid false positives.
    """
    if not raw_merchant:
        return None

    best_key = longest_substring_match(raw_merchant.lower(), mapping, bidirectional=False)
    return mapping[best_key] if best_key else None


def learn(mapping: dict, raw_merchant: str, name: str, category: str) -> None:
    """Add or update a merchant mapping and save to disk."""
    if not raw_merchant:
        return
    key = derive_key(raw_merchant)
    if not key:
        return
    mapping[key] = {"name": name, "category": category}
    save(mapping)
