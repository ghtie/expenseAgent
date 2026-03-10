"""Tests for merchant_store.py — derive_key, lookup, and learn."""

import json
import pytest
from expense_agent.stores import merchant_store


# ---------- derive_key ----------

class TestDeriveKey:
    def test_trader_joes(self):
        assert merchant_store.derive_key("TRADER JOE S #123") == "trader joe"

    def test_sq_prefix(self):
        assert merchant_store.derive_key("SQ *DELICA") == "delica"

    def test_tst_prefix(self):
        assert merchant_store.derive_key("TST* BLUE BOTTLE") == "blue bottle"

    def test_pp_prefix(self):
        assert merchant_store.derive_key("PP*SPOTIFY") == "spotify"

    def test_target(self):
        assert merchant_store.derive_key("TARGET T-") == "target"

    def test_daiso(self):
        assert merchant_store.derive_key("DAISO - JAPAN TOWN") == "daiso"

    def test_nijiya(self):
        assert merchant_store.derive_key("NIJIYA MARKET #62") == "nijiya market"

    def test_ups(self):
        result = merchant_store.derive_key("UPS*INTERNETSHIPWAYBIL")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_trailing_digits(self):
        assert merchant_store.derive_key("WALGREENS 12345") == "walgreens"

    def test_whitespace_collapse(self):
        assert merchant_store.derive_key("SOME  \n  STORE") == "some store"


# ---------- Lookup ----------

class TestLookup:
    def test_substring_match(self, sample_merchants):
        result = merchant_store.lookup(sample_merchants, "TRADER JOE S #123")
        assert result is not None
        assert result["name"] == "Trader Joes"

    def test_longest_wins(self):
        mapping = {
            "joe": {"name": "Joe's", "category": "Wrong"},
            "trader joe": {"name": "Trader Joes", "category": "Groceries"},
        }
        result = merchant_store.lookup(mapping, "TRADER JOE S #456")
        assert result["name"] == "Trader Joes"

    def test_empty_returns_none(self, sample_merchants):
        assert merchant_store.lookup(sample_merchants, "") is None

    def test_no_match_returns_none(self, sample_merchants):
        assert merchant_store.lookup(sample_merchants, "WHOLE FOODS") is None

    def test_skips_short_keys(self):
        mapping = {"TJ": {"name": "TJ's", "category": "Misc"}}
        assert merchant_store.lookup(mapping, "TJ STORE") is None


# ---------- Learn ----------

class TestLearn:
    def test_adds_entry(self, sample_merchants, monkeypatch):
        monkeypatch.setattr(merchant_store, "save", lambda *a: None)
        merchant_store.learn(sample_merchants, "SQ *DELICA", "Delica", "Food & Dining")
        assert "delica" in sample_merchants

    def test_saves_to_disk(self, sample_merchants, tmp_path, monkeypatch):
        path = tmp_path / "merchants.json"

        def save_to_tmp(mapping, p=None):
            with open(path, "w") as f:
                json.dump(mapping, f, indent=2)
                f.write("\n")

        monkeypatch.setattr(merchant_store, "save", save_to_tmp)
        merchant_store.learn(sample_merchants, "SQ *DELICA", "Delica", "Food & Dining")
        data = json.loads(path.read_text())
        assert "delica" in data

    def test_empty_merchant_noop(self, sample_merchants, monkeypatch):
        monkeypatch.setattr(merchant_store, "save", lambda *a: None)
        original = dict(sample_merchants)
        merchant_store.learn(sample_merchants, "", "Name", "Cat")
        assert sample_merchants == original

    def test_empty_derived_key_noop(self, sample_merchants, monkeypatch):
        monkeypatch.setattr(merchant_store, "save", lambda *a: None)
        original = dict(sample_merchants)
        # Whitespace-only raw merchant derives to empty key after strip
        merchant_store.learn(sample_merchants, "   ", "Name", "Cat")
        assert sample_merchants == original
