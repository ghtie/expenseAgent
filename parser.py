"""
Regex-based parsers for Capital One and Venmo transaction emails.

No external API calls — extracts date, merchant/item, and amount directly
from the email text using known email formats.
"""

import re
from datetime import datetime


class ParsingError(Exception):
    pass


# Capital One format (plain text from Gmail API has line breaks mid-sentence):
# "on February 21, 2026, at\nWWW.CSCSW.COM, a pending authorization or purchase
#  in the amount of $5.25\nwas placed or charged on your ..."
_CAPITALONE_PATTERN = re.compile(
    r"on\s+(?P<date>[A-Z][a-z]+\s+\d{1,2},\s*\d{4}),\s*"
    r"at\s+(?P<merchant>.+?),\s*"
    r"a\s+pending\s+authorization\s+or\s+purchase\s+in\s+the\s+amount\s+of\s+"
    r"\$(?P<amount>[\d,]+\.\d{2})",
    re.IGNORECASE | re.DOTALL,
)

# Fallback: broader pattern for Capital One template variations
# Matches: "A purchase was charged..." or "A transaction was made..." style emails
# Looks for any date, merchant after "at", and dollar amount nearby
_CAPITALONE_FALLBACK = re.compile(
    r"(?P<date>[A-Z][a-z]+\s+\d{1,2},\s*\d{4})"
    r".*?"
    r"at\s+(?P<merchant>.+?)"
    r",\s*(?:a\s+)?(?:purchase|transaction|charge|pending)"
    r".*?"
    r"\$(?P<amount>[\d,]+\.\d{2})",
    re.IGNORECASE | re.DOTALL,
)

# Venmo format (subject line):
# "Jeffrey He paid your $10.31 request"
_VENMO_SUBJECT_AMOUNT = re.compile(
    r"paid your \$(?P<amount>[\d,]+\.\d{2}) request",
    re.IGNORECASE,
)

# Venmo date in the transaction details section:
# "Date\nFeb 19, 2026" or "Date Feb 19, 2026"
_VENMO_DATE = re.compile(
    r"Date\s+(?P<date>[A-Z][a-z]{2}\s+\d{1,2},\s*\d{4})",
)

# Venmo note — appears between "paid you" amount and "See transaction"
# In plain text: "{Name} paid you\n$10.31\n{note}\nSee transaction"
_VENMO_NOTE = re.compile(
    r"paid you\s+\$[\d,.]+\s+(?P<note>.+?)\s+See transaction",
    re.DOTALL,
)


def _parse_date(date_str: str) -> str:
    """Convert a date string like 'February 19, 2026' or 'Feb 19, 2026' to MM/DD/YYYY."""
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%m/%d/%Y")
        except ValueError:
            continue
    raise ParsingError(f"Could not parse date: '{date_str}'")


def _clean_merchant(raw: str) -> str:
    """Clean up a Capital One merchant name into a readable item name."""
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
    cleaned = re.sub(r"\s+[A-Z]{0,2}-?\d*$", "", cleaned, flags=re.IGNORECASE)
    # Remove location suffixes like " - Japan Town"
    cleaned = re.sub(r"\s+-\s+\w[\w\s]*$", "", cleaned)
    # Remove trailing single character (truncated names like "JOE S" from "JOE'S")
    cleaned = re.sub(r"\s+[A-Za-z]$", "", cleaned)
    # Title-case it
    return cleaned.strip().title()


def parse_capitalone(email_text: str) -> dict:
    """Extract transaction from a Capital One alert email."""
    match = _CAPITALONE_PATTERN.search(email_text)

    if not match:
        # Try broader fallback pattern
        match = _CAPITALONE_FALLBACK.search(email_text)

    if not match:
        raise ParsingError(
            "Could not parse Capital One email. Expected format: "
            "'on {date}, at {merchant}, a pending authorization or purchase "
            "in the amount of ${amount}'"
        )

    return {
        "date": _parse_date(match.group("date")),
        "item": _clean_merchant(match.group("merchant")),
        "amount": float(match.group("amount").replace(",", "")),
        "category": "Misc",
        "_raw_merchant": match.group("merchant"),
    }


def parse_venmo(email_text: str, subject: str) -> dict:
    """Extract transaction from a Venmo payment email."""
    # Amount from subject line (most reliable)
    amount_match = _VENMO_SUBJECT_AMOUNT.search(subject)
    if not amount_match:
        raise ParsingError(
            "Could not parse Venmo amount from subject. "
            f"Expected format: '... paid your $X.XX request'. Got: '{subject}'"
        )
    amount = float(amount_match.group("amount").replace(",", ""))

    # Date from body
    date_match = _VENMO_DATE.search(email_text)
    if not date_match:
        raise ParsingError("Could not find date in Venmo email.")
    date = _parse_date(date_match.group("date"))

    # Note from body (the item description)
    note_match = _VENMO_NOTE.search(email_text)
    item = note_match.group("note").strip() if note_match else "Venmo Payment"

    return {
        "date": date,
        "item": item,
        "amount": amount,
        "category": "Misc",
        "_raw_merchant": "",
    }


def parse_transaction(email_text: str, source: str, subject: str = "") -> dict:
    """
    Parse a transaction from email text using regex.

    Args:
        email_text: Plain text email body.
        source: "capitalone" or "venmo".
        subject: Email subject line (needed for Venmo amount).

    Returns:
        dict with keys: date, category, item, amount

    Raises:
        ParsingError: if the email doesn't match the expected format.
    """
    if source == "capitalone":
        return parse_capitalone(email_text)
    if source == "venmo":
        return parse_venmo(email_text, subject)

    raise ParsingError(
        f"Unknown email source: '{source}'. "
        "Only Capital One and Venmo emails are supported."
    )
