"""
Gmail integration — fetch unread emails and mark them as read.

Requires a credentials.json file from Google Cloud Console (OAuth Desktop client).
On first run, opens a browser for OAuth consent and saves token.json for reuse.
"""

import base64
import os
from email import message_from_bytes

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# gmail.modify is the narrowest scope that allows read + mark-as-read
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def _get_service():
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Refresh token revoked or invalid — re-authenticate
                creds = None
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. "
                    "Download it from Google Cloud Console. "
                    "See GMAIL_SETUP.md for instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _extract_plain_text(payload: dict) -> str:
    """Recursively extract the plain-text body from a Gmail message payload."""
    mime_type = payload.get("mimeType", "")

    # Simple single-part message
    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        return ""

    # Multipart — recurse into parts
    parts = payload.get("parts", [])
    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    # If no text/plain found, try the first nested multipart
    for part in parts:
        text = _extract_plain_text(part)
        if text:
            return text

    return ""


def _extract_subject(headers: list[dict]) -> str:
    """Extract the Subject header from a list of Gmail message headers."""
    for header in headers:
        if header.get("name", "").lower() == "subject":
            return header.get("value", "")
    return ""


DEFAULT_GMAIL_QUERY = "is:unread from:(notification.capitalone.com OR venmo.com)"


def fetch_unread_emails(query: str = DEFAULT_GMAIL_QUERY) -> list[tuple[str, str, str]]:
    """
    Fetch unread emails matching the query.

    Returns:
        List of (message_id, subject, plain_text_body) tuples.
    """
    service = _get_service()

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=50,
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return []

    emails = []
    for msg_info in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_info["id"],
            format="full",
        ).execute()

        payload = msg.get("payload", {})
        subject = _extract_subject(payload.get("headers", []))
        body = _extract_plain_text(payload)
        timestamp = int(msg.get("internalDate", 0))
        if body.strip():
            emails.append((msg_info["id"], subject, body, timestamp))

    # Sort by timestamp so oldest emails are processed first
    emails.sort(key=lambda e: e[3])

    # Return without the timestamp field
    return [(mid, subj, body) for mid, subj, body, _ in emails]


def mark_as_read(message_id: str) -> None:
    """Remove the UNREAD label from a message."""
    service = _get_service()
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()
