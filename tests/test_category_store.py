"""Tests for category_store.py — load/save and fuzzy lookup."""

import json
import pytest
from expense_agent.stores import category_store


# ---------- Load / Save ----------

class TestLoadSave:
    def test_load_missing_returns_empty(self, tmp_path):
        assert category_store.load(str(tmp_path / "nope.json")) == {}

    def test_load_existing(self, tmp_path):
        path = tmp_path / "cats.json"
        path.write_text('{"Trader Joes": "Groceries"}')
        result = category_store.load(str(path))
        assert result == {"Trader Joes": "Groceries"}

    def test_save_creates_file(self, tmp_path):
        path = tmp_path / "cats.json"
        category_store.save({"A": "B"}, str(path))
        assert json.loads(path.read_text()) == {"A": "B"}

    def test_save_overwrites(self, tmp_path):
        path = tmp_path / "cats.json"
        category_store.save({"A": "B"}, str(path))
        category_store.save({"C": "D"}, str(path))
        assert json.loads(path.read_text()) == {"C": "D"}


# ---------- Lookup ----------

class TestLookup:
    def test_exact_match_case_insensitive(self, sample_categories):
        assert category_store.lookup(sample_categories, "trader joes") == "Groceries"

    def test_exact_preferred_over_fuzzy(self):
        mapping = {"Target": "Essentials", "Target Store": "Retail"}
        assert category_store.lookup(mapping, "Target") == "Essentials"

    def test_fuzzy_key_in_item(self, sample_categories):
        # Key "Trader Joes" is substring of item "Trader Joes Market #5"
        assert category_store.lookup(sample_categories, "Trader Joes Market #5") == "Groceries"

    def test_fuzzy_item_in_key(self):
        mapping = {"Trader Joe Market": "Groceries"}
        assert category_store.lookup(mapping, "Trader Joe") == "Groceries"

    def test_fuzzy_longest_wins(self):
        mapping = {"Joe": "Wrong", "Trader Joe": "Groceries"}
        assert category_store.lookup(mapping, "Trader Joe Market") == "Groceries"

    def test_skips_short_keys(self):
        mapping = {"TJ": "Groceries"}
        assert category_store.lookup(mapping, "TJ Market") is None

    def test_three_char_key_works(self):
        mapping = {"UPS": "Shipping"}
        assert category_store.lookup(mapping, "UPS Store") == "Shipping"

    def test_no_match_returns_none(self, sample_categories):
        assert category_store.lookup(sample_categories, "Unknown Store") is None
