import email
import sys
from pathlib import Path

SUPPORTED_SOURCES = ["capitalone", "venmo", "unknown"]


def get_email_text(file_path: str | None) -> str:
    """
    Return raw email text from a file path or interactive paste mode.

    Args:
        file_path: Path to a .txt or .eml file, or None for paste mode.

    Returns:
        The raw email text as a string.
    """
    if file_path is not None:
        return read_from_file(file_path)
    return read_from_paste()


def read_from_file(file_path: str) -> str:
    """Read email text from a .txt or .eml file."""
    path = Path(file_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() == ".eml":
        return _read_eml(path)

    # Treat everything else as plain text
    return path.read_text(encoding="utf-8")


def _read_eml(path: Path) -> str:
    """Extract the plain-text body from an .eml file."""
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw)

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset)
        # Fall back to first part if no plain-text found
        part = msg.get_payload(0)
        charset = part.get_content_charset() or "utf-8"
        return part.get_payload(decode=True).decode(charset)

    payload = msg.get_payload(decode=True)
    if payload:
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset)

    return msg.get_payload()


def read_from_paste() -> str:
    """
    Collect multi-line email text from the terminal.
    User types (or pastes) content and enters END on its own line to finish.
    """
    print("Paste your email below.")
    print('When done, press Enter, then type END on a new line and press Enter:\n')

    lines = []
    try:
        for line in sys.stdin:
            if line.rstrip("\n") == "END":
                break
            lines.append(line)
    except EOFError:
        pass  # Ctrl+D / Ctrl+Z — treat as end of input

    return "".join(lines)


def detect_source(email_text: str) -> str:
    """
    Detect the email provider from the email content.

    Returns source name (e.g. "capitalone", "venmo") or "unknown".
    Delegates to the parser registry so new sources only need one edit.
    """
    from parser import detect_source as _detect
    return _detect(email_text)
