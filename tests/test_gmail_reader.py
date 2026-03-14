"""Tests for gmail_reader.py — _extract_subject, _extract_plain_text, fetch/mark."""

import base64
import pytest
from unittest.mock import MagicMock, patch

from expense_agent.gmail_reader import _extract_subject, _extract_plain_text, _strip_html


# ---------- _extract_subject ----------

class TestExtractSubject:
    def test_finds_subject(self):
        headers = [
            {"name": "From", "value": "test@example.com"},
            {"name": "Subject", "value": "Payment received"},
        ]
        assert _extract_subject(headers) == "Payment received"

    def test_missing_subject(self):
        headers = [{"name": "From", "value": "test@example.com"}]
        assert _extract_subject(headers) == ""

    def test_case_insensitive(self):
        headers = [{"name": "SUBJECT", "value": "Test"}]
        assert _extract_subject(headers) == "Test"


# ---------- _extract_plain_text ----------

class TestExtractPlainText:
    def test_simple_text_plain(self):
        data = base64.urlsafe_b64encode(b"Hello world").decode()
        payload = {"mimeType": "text/plain", "body": {"data": data}}
        assert _extract_plain_text(payload) == "Hello world"

    def test_multipart(self):
        data = base64.urlsafe_b64encode(b"Body text").decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": data}},
                {"mimeType": "text/html", "body": {"data": "ignored"}},
            ],
        }
        assert _extract_plain_text(payload) == "Body text"

    def test_empty_payload(self):
        payload = {"mimeType": "text/html", "body": {"data": ""}}
        assert _extract_plain_text(payload) == ""

    def test_html_fallback_when_no_plain_text(self):
        """When only text/html is available, strip tags and return text."""
        html = "<p>Hello <b>world</b></p>"
        data = base64.urlsafe_b64encode(html.encode()).decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/html", "body": {"data": data}},
            ],
        }
        result = _extract_plain_text(payload)
        assert "Hello" in result
        assert "world" in result
        assert "<p>" not in result
        assert "<b>" not in result

    def test_plain_text_preferred_over_html(self):
        """When both text/plain and text/html exist, prefer plain text."""
        plain_data = base64.urlsafe_b64encode(b"Plain text body").decode()
        html_data = base64.urlsafe_b64encode(b"<p>HTML body</p>").decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": plain_data}},
                {"mimeType": "text/html", "body": {"data": html_data}},
            ],
        }
        assert _extract_plain_text(payload) == "Plain text body"

    def test_venmo_html_email_parses(self):
        """End-to-end: a Venmo HTML-only email should extract parseable text."""
        html = """
        <html><body>
        <p>Jeffrey He paid you</p>
        <p>$10.31</p>
        <p>Dinner split</p>
        <p>See transaction details</p>
        <br>
        <p>Date</p>
        <p>Feb 19, 2026</p>
        <p>Powered by venmo.com</p>
        </body></html>
        """
        data = base64.urlsafe_b64encode(html.encode()).decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/html", "body": {"data": data}},
            ],
        }
        text = _extract_plain_text(payload)
        # Verify the extracted text contains what the parser needs
        assert "venmo" in text.lower()
        assert "paid you" in text
        assert "$10.31" in text
        assert "Feb 19, 2026" in text
        assert "Date" in text

        # Verify it actually parses
        from expense_agent.parser import detect_source, parse_transaction
        source = detect_source(text)
        assert source == "venmo"
        txn = parse_transaction(text, source, subject="Jeffrey He paid your $10.31 request")
        assert txn["amount"] == 10.31
        assert txn["date"] == "02/19/2026"

    def test_venmo_html_with_style_block(self):
        """Realistic Venmo HTML with <style> CSS should strip cleanly."""
        html = """
        <html><head>
        <style type="text/css">
        @media only screen{html{min-height:100%;background:#faf7f2}}
        @media only screen and (max-width:596px){table.body img{width:auto}}
        .card-container .profile-image img{width:60px!important}
        </style>
        </head><body>
        <p>You paid Jeffrey He</p>
        <p>$<span style="font-size:48px">343</span>.<span>50</span></p>
        <p>Google web pass</p>
        <p>See transaction</p>
        <p>Transaction details</p>
        <p>Date</p>
        <p>Mar 13, 2026</p>
        <p>Venmo RT</p>
        </body></html>
        """
        data = base64.urlsafe_b64encode(html.encode()).decode()
        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/html", "body": {"data": data}},
            ],
        }
        text = _extract_plain_text(payload)
        # CSS should be completely gone
        assert "@media" not in text
        assert "min-height" not in text
        # Content should be intact
        assert "You paid Jeffrey He" in text
        assert "Google web pass" in text
        assert "Mar 13, 2026" in text

        from expense_agent.parser import detect_source, parse_transaction
        source = detect_source(text)
        assert source == "venmo"
        txn = parse_transaction(text, source, subject="You paid Jeffrey He $343.50")
        assert txn["amount"] == 343.50
        assert txn["date"] == "03/13/2026"
        assert txn["item"] == "Google web pass"


# ---------- _strip_html ----------

class TestStripHtml:
    def test_strips_tags(self):
        assert "Hello" in _strip_html("<b>Hello</b>")
        assert "<b>" not in _strip_html("<b>Hello</b>")

    def test_br_to_newline(self):
        result = _strip_html("Line 1<br>Line 2")
        assert "Line 1" in result
        assert "Line 2" in result

    def test_entities(self):
        result = _strip_html("A &amp; B &lt; C")
        assert "A & B < C" in result

    def test_strips_style_blocks(self):
        html = '<style type="text/css">body{color:red} .foo{margin:0}</style><p>Hello</p>'
        result = _strip_html(html)
        assert "Hello" in result
        assert "color:red" not in result
        assert ".foo" not in result

    def test_strips_script_blocks(self):
        html = '<script>var x = 1;</script><p>Content</p>'
        result = _strip_html(html)
        assert "Content" in result
        assert "var x" not in result


# ---------- fetch_unread_emails ----------

class TestFetchUnreadEmails:
    def test_returns_tuples(self):
        body_data = base64.urlsafe_b64encode(b"Email body").decode()
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}]
        }
        mock_service.users().messages().get().execute.return_value = {
            "id": "msg1",
            "internalDate": "1000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [{"name": "Subject", "value": "Test subject"}],
                "body": {"data": body_data},
            },
        }
        with patch("expense_agent.gmail_reader._get_service", return_value=mock_service):
            from expense_agent.gmail_reader import fetch_unread_emails
            result = fetch_unread_emails()
        assert len(result) == 1
        assert result[0][0] == "msg1"
        assert result[0][1] == "Test subject"

    def test_empty(self):
        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {}
        with patch("expense_agent.gmail_reader._get_service", return_value=mock_service):
            from expense_agent.gmail_reader import fetch_unread_emails
            result = fetch_unread_emails()
        assert result == []

    def test_sorts_by_timestamp(self):
        def make_msg(msg_id, ts):
            data = base64.urlsafe_b64encode(b"body").decode()
            return {
                "id": msg_id,
                "internalDate": str(ts),
                "payload": {
                    "mimeType": "text/plain",
                    "headers": [{"name": "Subject", "value": f"Subj {msg_id}"}],
                    "body": {"data": data},
                },
            }

        mock_service = MagicMock()
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "b"}, {"id": "a"}]
        }
        # Return different messages based on call order
        mock_service.users().messages().get().execute.side_effect = [
            make_msg("b", 2000),
            make_msg("a", 1000),
        ]
        with patch("expense_agent.gmail_reader._get_service", return_value=mock_service):
            from expense_agent.gmail_reader import fetch_unread_emails
            result = fetch_unread_emails()
        assert result[0][0] == "a"  # older first
        assert result[1][0] == "b"


# ---------- mark_as_read ----------

class TestMarkAsRead:
    def test_calls_modify(self):
        mock_service = MagicMock()
        with patch("expense_agent.gmail_reader._get_service", return_value=mock_service):
            from expense_agent.gmail_reader import mark_as_read
            mark_as_read("msg123")
        mock_service.users().messages().modify.assert_called_once_with(
            userId="me",
            id="msg123",
            body={"removeLabelIds": ["UNREAD"]},
        )
