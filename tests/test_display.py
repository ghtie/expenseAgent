"""Tests for display.py — _parse_numbers, show_batch_table, prompt_category."""

import pytest
from io import StringIO
from unittest.mock import patch

from display import _parse_numbers, show_batch_table, prompt_category, console


# ---------- _parse_numbers ----------

class TestParseNumbers:
    def test_space_separated(self):
        assert _parse_numbers("1 2 3", 5) == [0, 1, 2]

    def test_comma_separated(self):
        assert _parse_numbers("1,2,3", 5) == [0, 1, 2]

    def test_comma_space(self):
        assert _parse_numbers("1, 2, 3", 5) == [0, 1, 2]

    def test_single(self):
        assert _parse_numbers("3", 5) == [2]

    def test_out_of_range(self):
        assert _parse_numbers("6", 5) is None

    def test_non_numeric(self):
        assert _parse_numbers("abc", 5) is None

    def test_empty(self):
        assert _parse_numbers("", 5) is None


# ---------- show_batch_table ----------

class TestShowBatchTable:
    def test_smoke(self):
        """Verify show_batch_table renders without crashing."""
        transactions = [
            {"date": "02/21/2026", "item": "Test", "category": "Misc", "amount": 5.25},
        ]
        statuses = ["pending"]
        # Should not raise
        out = StringIO()
        test_console = console.__class__(file=out, force_terminal=True)
        with patch.object(
            __import__("display"), "console", test_console
        ):
            show_batch_table(transactions, statuses)
        output = out.getvalue()
        assert len(output) > 0


# ---------- prompt_category ----------

class TestPromptCategory:
    def test_enter_keeps_current(self, monkeypatch):
        monkeypatch.setattr(console, "input", lambda _: "")
        result = prompt_category("Groceries")
        assert result == "Groceries"

    def test_number_selection(self, monkeypatch):
        monkeypatch.setattr(console, "input", lambda _: "1")
        result = prompt_category("Misc")
        assert result == "Apartment Necessities"  # first in CATEGORIES list

    def test_fuzzy_single_match(self, monkeypatch):
        monkeypatch.setattr(console, "input", lambda _: "grocer")
        result = prompt_category("Misc")
        assert result == "Groceries"
