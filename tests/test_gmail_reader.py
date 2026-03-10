"""Tests for gmail_reader.py — _extract_subject, _extract_plain_text, fetch/mark."""

import base64
import pytest
from unittest.mock import MagicMock, patch

from expense_agent.gmail_reader import _extract_subject, _extract_plain_text


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
