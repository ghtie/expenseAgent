"""
Regex-based parsers for Capital One and Venmo transaction emails.

No external API calls — extracts date, merchant/item, and amount directly
from the email text using known email formats.
"""

import re
from datetime import datetime

from expense_agent.utils.merchant_utils import normalize_merchant


class ParsingError(Exception):
    pass


# Capital One format (plain text from Gmail API has line breaks mid-sentence):
# "on February 21, 2026, at\nWWW.CSCSW.COM, a pending authorization or purchase
#  in the amount of $5.25\nwas placed or charged on your ..."
_CAPITALONE_PATTERN = re.compile(
    r"on\s+(?P<date>[A-Z][a-z]+\.?\s+\d{1,2},\s*\d{4}),\s*"
    r"at\s+(?P<merchant>.+?),\s*"
    r"a\s+pending\s+authorization\s+or\s+purchase\s+in\s+the\s+amount\s+of\s+"
    r"\$(?P<amount>[\d,]+\.\d{2})",
    re.IGNORECASE | re.DOTALL,
)

# Fallback: broader pattern for Capital One template variations
# Matches: "A purchase was charged..." or "A transaction was made..." style emails
# Looks for any date, merchant after "at", and dollar amount nearby
_CAPITALONE_FALLBACK = re.compile(
    r"(?P<date>[A-Z][a-z]+\.?\s+\d{1,2},\s*\d{4})"
    r".*?"
    r"at\s+(?P<merchant>.+?)"
    r",\s*(?:a\s+)?(?:purchase|transaction|charge|pending)"
    r".*?"
    r"\$(?P<amount>[\d,]+\.\d{2})",
    re.IGNORECASE | re.DOTALL,
)

# Venmo subject amount patterns:
# Outgoing: "You paid Jeffrey He $343.50"
# Incoming (kept as fallback): "Jeffrey He paid your $10.31 request"
_VENMO_SUBJECT_OUTGOING = re.compile(
    r"You paid .+\$(?P<amount>[\d,]+\.\d{2})",
    re.IGNORECASE,
)
_VENMO_SUBJECT_INCOMING = re.compile(
    r"paid your \$(?P<amount>[\d,]+\.\d{2}) request",
    re.IGNORECASE,
)

# Venmo date in the transaction details section:
# "Date\nFeb 19, 2026" or "Date Feb 19, 2026"
_VENMO_DATE = re.compile(
    r"Date\s+(?P<date>[A-Z][a-z]{2}\s+\d{1,2},\s*\d{4})",
)

# Venmo note — the non-empty, non-dollar line right before "See transaction"
# Works for both incoming and outgoing:
#   "...$10.31\nDinner split\nSee transaction details"
#   "...$ 343 . 50\nGoogle web pass\nSee transaction"
_VENMO_NOTE = re.compile(
    r"\n(?P<note>[^$\n][^\n]+)\n\s*See transaction",
)

# Bank of America HTML alert emails (after HTML stripping) contain:
#   Amount:  $95.57
#   Date:    August 11, 2026
#   Where:   WEEE INC.
_BOFA_AMOUNT = re.compile(r"Amount:\s*\*?\$(?P<amount>[\d,]+\.\d{2})\*?", re.IGNORECASE)
_BOFA_DATE = re.compile(r"Date:\s*\*?(?P<date>[A-Z][a-z]+\.?\s+\d{1,2},\s*\d{4})\*?", re.IGNORECASE)
_BOFA_WHERE = re.compile(r"Where:\s*\*?(?P<merchant>[^\n*]+)\*?", re.IGNORECASE)


def _parse_date(date_str: str) -> str:
    """Convert a date string like 'February 19, 2026' or 'Feb 19, 2026' or 'Apr. 25, 2026' to MM/DD/YYYY."""
    cleaned = date_str.strip().replace(".", "")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).strftime("%m/%d/%Y")
        except ValueError:
            continue
    raise ParsingError(f"Could not parse date: '{date_str}'")


def _clean_merchant(raw: str) -> str:
    """Clean up a Capital One merchant name into a readable item name."""
    return normalize_merchant(raw).title()


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
        "subcategory": "Misc",
        "_raw_merchant": match.group("merchant"),
    }


def parse_venmo(email_text: str, subject: str) -> dict:
    """Extract transaction from a Venmo payment email (incoming or outgoing)."""
    # Amount from subject line (most reliable — body amount may lose decimal from HTML)
    amount_match = _VENMO_SUBJECT_OUTGOING.search(subject)
    if not amount_match:
        amount_match = _VENMO_SUBJECT_INCOMING.search(subject)
    if not amount_match:
        raise ParsingError(
            "Could not parse Venmo amount from subject. "
            "Expected: '... paid your $X.XX request' or 'You paid Name $X.XX'. "
            f"Got: '{subject}'"
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
        "subcategory": "Misc",
        "_raw_merchant": "",
    }


def parse_bofa(email_text: str) -> dict:
    """Extract transaction from a Bank of America alert email."""
    amount_match = _BOFA_AMOUNT.search(email_text)
    if not amount_match:
        raise ParsingError("Could not parse Bank of America email: no amount found.")

    date_match = _BOFA_DATE.search(email_text)
    if not date_match:
        raise ParsingError("Could not parse Bank of America email: no date found.")

    where_match = _BOFA_WHERE.search(email_text)
    if not where_match:
        raise ParsingError("Could not parse Bank of America email: no merchant found.")

    raw_merchant = where_match.group("merchant").strip()

    return {
        "date": _parse_date(date_match.group("date")),
        "item": _clean_merchant(raw_merchant),
        "amount": float(amount_match.group("amount").replace(",", "")),
        "category": "Misc",
        "subcategory": "Misc",
        "_raw_merchant": raw_merchant,
    }


def _detect_capitalone(email_text: str) -> bool:
    text_lower = email_text.lower()
    return "capital one" in text_lower or "capitalone.com" in text_lower


def _detect_venmo(email_text: str) -> bool:
    text_lower = email_text.lower()
    return "venmo" in text_lower or "venmo.com" in text_lower


def _detect_bofa(email_text: str) -> bool:
    text_lower = email_text.lower()
    return "bank of america" in text_lower or "bankofamerica.com" in text_lower


# Registry mapping source name → detect function and parse function.
# To add a new email source, add an entry here — no other files need editing.
PARSERS: dict[str, dict] = {
    "capitalone": {
        "detect": _detect_capitalone,
        "parse": lambda text, subject: parse_capitalone(text),
    },
    "venmo": {
        "detect": _detect_venmo,
        "parse": lambda text, subject: parse_venmo(text, subject),
    },
    "bofa": {
        "detect": _detect_bofa,
        "parse": lambda text, subject: parse_bofa(text),
    },
}


def detect_source(email_text: str) -> str:
    """Detect the email provider from the email content. Returns source name or 'unknown'."""
    for name, entry in PARSERS.items():
        if entry["detect"](email_text):
            return name
    return "unknown"


def parse_transaction(email_text: str, source: str, subject: str = "") -> dict:
    """
    Parse a transaction from email text using regex.

    Args:
        email_text: Plain text email body.
        source: Source name from detect_source() (e.g. "capitalone", "venmo").
        subject: Email subject line (needed for Venmo amount).

    Returns:
        dict with keys: date, category, item, amount

    Raises:
        ParsingError: if the email doesn't match the expected format.
    """
    entry = PARSERS.get(source)
    if entry is None:
        raise ParsingError(
            f"Unknown email source: '{source}'. "
            f"Supported sources: {', '.join(PARSERS.keys())}."
        )
    return entry["parse"](email_text, subject)
