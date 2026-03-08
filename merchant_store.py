"""Merchant auto-learn: maps raw merchant substrings to canonical name + category."""

import json
import os
import re

DEFAULT_PATH = "merchants.json"


def load(path: str = DEFAULT_PATH) -> dict:
    """Read merchants.json. Returns {} if missing."""
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def save(mapping: dict, path: str = DEFAULT_PATH) -> None:
    """Write merchants.json to disk."""
    with open(path, "w") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        f.write("\n")


def derive_key(raw_merchant: str) -> str:
    """
    Derive a stable lookup key from a raw merchant string.

    Lowercases, collapses whitespace, strips trailing store codes/numbers/
    location suffixes so the key generalizes across branches.
    E.g. "TRADER JOE S #123" -> "trader joe"
    """
    key = raw_merchant.strip().lower()
    key = re.sub(r"\s+", " ", key)
    # Strip payment processor prefixes
    key = re.sub(r"^(sq|tst|pp)\s*\*\s*", "", key)
    # Strip trailing #NNN store numbers
    key = re.sub(r"\s*#\d+$", "", key)
    # Strip trailing pure digit codes (3+ digits)
    key = re.sub(r"\s+\d{3,}$", "", key)
    # Strip trailing short codes like T- or T-1234
    key = re.sub(r"\s+[a-z]{0,2}-?\d*$", "", key)
    # Strip location suffixes like " - japan town"
    key = re.sub(r"\s+-\s+\w[\w\s]*$", "", key)
    # Strip trailing single character (truncated names like "joe s")
    key = re.sub(r"\s+[a-z]$", "", key)
    return key.strip()


def lookup(mapping: dict, raw_merchant: str) -> dict | None:
    """
    Case-insensitive substring match against raw merchant string.
    Returns {"name": "...", "category": "..."} or None.
    Longest match wins to avoid false positives.
    """
    if not raw_merchant:
        return None

    raw_lower = raw_merchant.lower()
    best_key = None
    best_len = 0

    for key in mapping:
        if len(key) < 3:
            continue
        if key in raw_lower:
            if len(key) > best_len:
                best_key = key
                best_len = len(key)

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
