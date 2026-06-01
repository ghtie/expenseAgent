"""Tests for main.py — load_config, _parse_email, _write_transaction, run_undo, run_gmail."""

import json
import sys
import pytest
from unittest.mock import patch, MagicMock

import expense_agent
from expense_agent import main
from expense_agent.main import load_config, _parse_email, _write_transaction, run_undo, run_gmail


# ---------- load_config ----------

class TestLoadConfig:
    def test_valid(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text('{"excel_path": "test.xlsx", "sheet_name": "Sheet1"}')
        result = load_config(str(cfg))
        assert result["excel_path"] == "test.xlsx"

    def test_missing_exits(self, tmp_path):
        with pytest.raises(SystemExit):
            load_config(str(tmp_path / "nope.json"))

    def test_invalid_json_exits(self, tmp_path):
        cfg = tmp_path / "config.json"
        cfg.write_text("{bad json")
        with pytest.raises(SystemExit):
            load_config(str(cfg))


# ---------- _parse_email ----------

class TestParseEmail:
    def test_merchant_match(self, sample_capitalone_email, sample_categories, sample_merchants):
        merchants = {"cscsw": {"name": "CSCSW Service", "subcategory": "Subscriptions"}}
        result = _parse_email(sample_capitalone_email, "", sample_categories, merchants)
        assert result is not None
        assert result["item"] == "CSCSW Service"
        assert result["subcategory"] == "Subscriptions"
        assert result["category"] == "Subscriptions"  # derived from subcategory

    def test_category_fallback(self, sample_categories):
        email = (
            "Capital One alert\n"
            "on March 10, 2026, at\n"
            "TRADER JOE S #123, a pending authorization or purchase "
            "in the amount of $42.99\n"
            "was placed on your card."
        )
        result = _parse_email(email, "", sample_categories, {})
        assert result is not None
        # "Trader Joe" should fuzzy-match "Trader Joes" in categories
        assert result["subcategory"] == "Groceries"
        assert result["category"] == "Food & Dining"

    def test_no_match(self, sample_categories, sample_merchants):
        email = (
            "Capital One alert\n"
            "on March 10, 2026, at\n"
            "BRAND NEW STORE, a pending authorization or purchase "
            "in the amount of $10.00\n"
            "was placed on your card."
        )
        result = _parse_email(email, "", sample_categories, sample_merchants)
        assert result is not None
        assert result["subcategory"] == "Misc"

    def test_unknown_source(self, sample_categories, sample_merchants):
        result = _parse_email("Hello from your bank", "", sample_categories, sample_merchants)
        assert result is None

    def test_empty_text(self, sample_categories, sample_merchants):
        result = _parse_email("   ", "", sample_categories, sample_merchants)
        assert result is None

    def test_parse_error(self, sample_categories, sample_merchants):
        # Has "capital one" to trigger source detection, but no parseable pattern
        result = _parse_email("Capital One says hello!", "", sample_categories, sample_merchants)
        assert result is None


# ---------- _write_transaction ----------

class TestWriteTransaction:
    def test_success(self, config, monkeypatch):
        monkeypatch.setattr("expense_agent.main.category_store.save", lambda *a: None)
        monkeypatch.setattr("expense_agent.main.merchant_store.learn", lambda *a: None)
        txn = {"date": "02/21/2026", "item": "Test", "category": "Misc", "subcategory": "Misc", "amount": 5.25}
        result = _write_transaction(config, txn, "RAW", {}, {})
        assert result is True

    def test_excel_error(self, tmp_path, monkeypatch):
        cfg = {"excel_path": str(tmp_path / "nope.xlsx"), "sheet_name": "Sheet1"}
        txn = {"date": "02/21/2026", "item": "Test", "category": "Misc", "subcategory": "Misc", "amount": 5.25}
        result = _write_transaction(cfg, txn, "", {}, {})
        assert result is False

    def test_updates_categories(self, config, monkeypatch):
        saved = {}
        monkeypatch.setattr("expense_agent.main.category_store.save", lambda m, *a: saved.update(m))
        monkeypatch.setattr("expense_agent.main.merchant_store.learn", lambda *a: None)
        categories = {}
        txn = {"date": "02/21/2026", "item": "Coffee", "category": "Food & Dining",
               "subcategory": "Dining", "amount": 4.50}
        _write_transaction(config, txn, "", categories, {})
        assert categories["Coffee"] == "Dining"

    def test_marks_processed(self, config, monkeypatch):
        monkeypatch.setattr("expense_agent.main.category_store.save", lambda *a: None)
        monkeypatch.setattr("expense_agent.main.merchant_store.learn", lambda *a: None)
        monkeypatch.setattr("expense_agent.main.dedup_store.mark_processed", lambda ids, mid: ids.add(mid))
        processed = set()
        txn = {"date": "02/21/2026", "item": "Test", "category": "Misc", "subcategory": "Misc", "amount": 5.25}
        _write_transaction(config, txn, "", {}, {}, processed, "msg123")
        assert "msg123" in processed

    def test_no_dedup_without_msg_id(self, config, monkeypatch):
        monkeypatch.setattr("expense_agent.main.category_store.save", lambda *a: None)
        monkeypatch.setattr("expense_agent.main.merchant_store.learn", lambda *a: None)
        mark_called = []
        monkeypatch.setattr("expense_agent.main.dedup_store.mark_processed", lambda *a: mark_called.append(1))
        txn = {"date": "02/21/2026", "item": "Test", "category": "Misc", "subcategory": "Misc", "amount": 5.25}
        _write_transaction(config, txn, "", {}, {}, set(), "")
        assert len(mark_called) == 0


# ---------- run_undo ----------

class TestRunUndo:
    def test_removes_row(self, config, monkeypatch):
        from expense_agent.excel_writer import append_row
        txn = {"date": "02/21/2026", "item": "Test", "category": "Misc", "subcategory": "Misc", "amount": 5.25}
        append_row(config, txn)
        # Should not raise or exit
        run_undo(config)

    def test_empty_sheet(self, config):
        # Should not raise — just prints info
        run_undo(config)

    def test_excel_error_exits(self, tmp_path):
        cfg = {"excel_path": str(tmp_path / "nope.xlsx"), "sheet_name": "Sheet1"}
        with pytest.raises(SystemExit):
            run_undo(cfg)


# ---------- run_gmail ----------

class TestRunGmail:
    def _setup_gmail_mocks(self, monkeypatch, emails, parse_result=None):
        """Helper to set up common gmail mocks."""
        mock_gmail = MagicMock()
        mock_gmail.fetch_unread_emails.return_value = emails
        mock_gmail.mark_as_read = MagicMock()
        # Inject mock so `from expense_agent import gmail_reader` inside run_gmail gets it
        monkeypatch.setitem(sys.modules, "expense_agent.gmail_reader", mock_gmail)
        monkeypatch.setattr(expense_agent, "gmail_reader", mock_gmail, raising=False)
        monkeypatch.setattr("expense_agent.main.dedup_store.load", lambda: set())
        monkeypatch.setattr("expense_agent.main.dedup_store.mark_processed", lambda ids, mid: ids.add(mid))
        monkeypatch.setattr("expense_agent.main.category_store.save", lambda *a: None)
        monkeypatch.setattr("expense_agent.main.merchant_store.learn", lambda *a: None)
        return mock_gmail

    def test_no_emails(self, config, monkeypatch):
        mock_gmail = self._setup_gmail_mocks(monkeypatch, [])
        # Should not raise
        run_gmail(config, {}, {})

    def test_all_write(self, config, monkeypatch, sample_capitalone_email):
        emails = [("msg1", "Subject", sample_capitalone_email)]
        mock_gmail = self._setup_gmail_mocks(monkeypatch, emails)
        monkeypatch.setattr("expense_agent.main.display.prompt_batch_action", lambda n: ("all", None))
        run_gmail(config, {}, {})
        mock_gmail.mark_as_read.assert_called_once_with("msg1")

    def test_skip_some(self, config, monkeypatch, sample_capitalone_email):
        emails = [("msg1", "Subject", sample_capitalone_email)]
        mock_gmail = self._setup_gmail_mocks(monkeypatch, emails)
        call_count = [0]

        def mock_batch_action(n):
            call_count[0] += 1
            if call_count[0] == 1:
                return ("skip", [0])
            return ("all", None)

        monkeypatch.setattr("expense_agent.main.display.prompt_batch_action", mock_batch_action)
        run_gmail(config, {}, {})
        mock_gmail.mark_as_read.assert_not_called()

    def test_dedup_skips(self, config, monkeypatch, sample_capitalone_email):
        emails = [("msg1", "Subject", sample_capitalone_email)]
        mock_gmail = self._setup_gmail_mocks(monkeypatch, emails)
        monkeypatch.setattr("expense_agent.main.dedup_store.load", lambda: {"msg1"})
        run_gmail(config, {}, {})
        mock_gmail.mark_as_read.assert_not_called()

    def test_edit_then_write(self, config, monkeypatch, sample_capitalone_email):
        emails = [("msg1", "Subject", sample_capitalone_email)]
        mock_gmail = self._setup_gmail_mocks(monkeypatch, emails)
        call_count = [0]

        def mock_batch_action(n):
            call_count[0] += 1
            if call_count[0] == 1:
                return ("edit", [0])
            return ("all", None)

        def mock_prompt_edit(txn):
            txn["item"] = "Edited Item"

        monkeypatch.setattr("expense_agent.main.display.prompt_batch_action", mock_batch_action)
        monkeypatch.setattr("expense_agent.main.display.prompt_edit", mock_prompt_edit)
        run_gmail(config, {}, {})
        mock_gmail.mark_as_read.assert_called_once()
