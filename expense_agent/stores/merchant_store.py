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
    Returns {"name": "...", "subcategory": "..."} or None.
    Longest match wins to avoid false positives.
    Handles legacy entries that use "category" instead of "subcategory".
    """
    if not raw_merchant:
        return None

    best_key = longest_substring_match(raw_merchant.lower(), mapping, bidirectional=False)
    if not best_key:
        return None
    entry = mapping[best_key]
    # Handle legacy format: {"name": "...", "category": "..."}
    if "subcategory" not in entry and "category" in entry:
        return {"name": entry["name"], "subcategory": entry["category"]}
    return entry


def learn(mapping: dict, raw_merchant: str, name: str, subcategory: str) -> None:
    """Add or update a merchant mapping and save to disk."""
    if not raw_merchant:
        return
    key = derive_key(raw_merchant)
    if not key:
        return
    mapping[key] = {"name": name, "subcategory": subcategory}
    save(mapping)
