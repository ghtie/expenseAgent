"""Shared merchant name normalization used by parser and merchant_store."""

import re


def normalize_merchant(raw: str) -> str:
    """
    Normalize a raw merchant string into a stable, lowercase key.

    Collapses whitespace, strips WWW/TLD prefixes/suffixes, payment processor
    prefixes, trailing store codes, location suffixes, and trailing single chars.
    """
    cleaned = raw.strip()
    # Collapse any whitespace/newlines into single spaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Strip "WWW." prefix and ".COM"/".NET"/etc suffix for URLs
    cleaned = re.sub(r"^WWW\.", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\.(COM|NET|ORG)$", "", cleaned, flags=re.IGNORECASE)
    # Strip payment processor prefixes (SQ *, TST *, PP*)
    cleaned = re.sub(r"^(SQ|TST|PP)\s*\*\s*", "", cleaned, flags=re.IGNORECASE)
    # Remove trailing store/location codes: #62, T-1234, T-, etc.
    cleaned = re.sub(r"\s*#\d+$", "", cleaned)
    cleaned = re.sub(r"\s+\d{3,}$", "", cleaned)
    cleaned = re.sub(r"\s+[A-Za-z]{0,2}-?\d*$", "", cleaned, flags=re.IGNORECASE)
    # Remove location suffixes like " - Japan Town"
    cleaned = re.sub(r"\s+-\s+\w[\w\s]*$", "", cleaned)
    # Remove trailing single character (truncated names like "joe s")
    cleaned = re.sub(r"\s+[A-Za-z]$", "", cleaned)
    return cleaned.strip().lower()
