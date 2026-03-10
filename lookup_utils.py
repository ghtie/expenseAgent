"""Shared fuzzy substring matching for category and merchant lookups."""


def longest_substring_match(
    query_lower: str,
    keys: dict,
    min_len: int = 3,
    bidirectional: bool = False,
) -> str | None:
    """
    Find the longest key that is a substring of query_lower (or vice versa
    if bidirectional=True). Returns the original key or None.

    Args:
        query_lower: Lowercased search string.
        keys: Dict whose keys are the candidates to match against.
        min_len: Minimum key length to consider (avoids false positives).
        bidirectional: If True, also matches when query_lower is a substring of the key.
    """
    best_key = None
    best_len = 0

    for key in keys:
        key_lower = key.lower()
        if len(key_lower) < min_len:
            continue
        matched = key_lower in query_lower
        if not matched and bidirectional:
            matched = query_lower in key_lower
        if matched and len(key_lower) > best_len:
            best_key = key
            best_len = len(key_lower)

    return best_key
