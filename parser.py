import json
import os
import re

import anthropic


class ParsingError(Exception):
    pass


SYSTEM_PROMPT = """You are a financial data extraction assistant. Extract transaction data from \
financial notification emails and return structured JSON.

Classify into exactly one category from this list:
Apartment Necessities, Clothing & Shoes, Education, Electricity, Entertainment, \
Essentials, Food & Dining, Gift, Groceries, Health, Hobbies, Misc, Phone, \
School, Skincare & Makeup, Special Events, Subscriptions, Transportation, \
Travel - Flight, Travel - Food & Dining, Travel - Hotel, Travel - Misc, \
Travel - Special Events, Travel - Transportation, Utilities

Rules:
- date: MM/DD/YYYY format
- amount: positive float, no dollar sign, no commas
- item: the core merchant or brand name only, with proper capitalization. \
Strip away prefixes, suffixes, and filler words (e.g. "dinner at", "purchase at", \
"payment to", location suffixes, transaction IDs). \
Examples: "Dinner at Nobu Malibu" → "Nobu", "UBER EATS" → "Uber Eats", \
"amazon.com" → "Amazon", "SQ *Blue Bottle Coffee" → "Blue Bottle Coffee", \
"Netflix Monthly Sub" → "Netflix"
- category: must be chosen from the list above — pick the single best match
- Return ONLY a ```json ... ``` fenced JSON object. No other text.
- If a field cannot be determined, set it to null."""

# Source-specific user prompts. To add a new email provider:
# 1. Add a detection rule in email_reader.detect_source()
# 2. Add a prompt entry here with the same key name
SOURCE_PROMPTS = {
    "capitalone": (
        "Here is a Capital One credit card transaction alert:\n---\n{email_text}\n---\n"
        "Extract the transaction and return the JSON."
    ),
    "venmo": (
        "Here is a Venmo payment notification:\n---\n{email_text}\n---\n"
        "Extract the payment as a transaction. The 'item' should be the Venmo payment "
        "note/memo if one exists, otherwise use the sender's or recipient's name. "
        "The amount is the dollar value that was paid or charged. Return the JSON."
    ),
    "unknown": (
        "Here is a financial notification email:\n---\n{email_text}\n---\n"
        "Extract any transaction details you can find and return the JSON."
    ),
}


def parse_transaction(email_text: str, source: str, config: dict) -> dict:
    """
    Call the Claude API to extract and categorize a transaction from email text.

    Args:
        email_text: Raw email body text.
        source: Provider key from email_reader.detect_source() (e.g. "capitalone").
        config: Loaded config.json dict (must contain "model" key).

    Returns:
        dict with keys: date (str), category (str), item (str), amount (float)

    Raises:
        ParsingError: if Claude's response cannot be parsed or required fields are null.
    """
    user_prompt_template = SOURCE_PROMPTS.get(source, SOURCE_PROMPTS["unknown"])
    user_prompt = user_prompt_template.format(email_text=email_text)

    system_prompt = SYSTEM_PROMPT

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    try:
        message = client.messages.create(
            model=config.get("model", "claude-opus-4-6"),
            max_tokens=512,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as exc:
        raise ParsingError(f"Claude API error: {exc}")

    response_text = message.content[0].text
    data = _extract_json(response_text)

    # Validate required fields
    missing = [field for field in ("date", "category", "item", "amount") if data.get(field) is None]
    if missing:
        raise ParsingError(
            f"Could not extract the following fields from the email: {', '.join(missing)}.\n"
            "Make sure you pasted a valid Capital One or Venmo notification."
        )

    return {
        "date": str(data["date"]),
        "category": str(data["category"]),
        "item": str(data["item"]),
        "amount": float(data["amount"]),
    }


def _extract_json(response_text: str) -> dict:
    """
    Extract a JSON object from Claude's response.

    Handles both fenced (```json ... ```) and bare JSON responses.

    Raises:
        ParsingError: if no valid JSON object is found.
    """
    # Try to find a ```json ... ``` block first
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
    if fenced:
        json_str = fenced.group(1)
    else:
        # Fall back: look for the first {...} in the response
        bare = re.search(r"\{.*?\}", response_text, re.DOTALL)
        if bare:
            json_str = bare.group(0)
        else:
            raise ParsingError(
                "Could not find JSON in Claude's response.\n"
                f"Raw response: {response_text[:200]}"
            )

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ParsingError(f"Failed to parse JSON from Claude's response: {exc}")
