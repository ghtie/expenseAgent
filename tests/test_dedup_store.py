"""Tests for dedup_store.py — load, save, is_processed, mark_processed."""

import json
import pytest
from expense_agent.stores import dedup_store


class TestDedupStore:
    def test_load_missing(self, tmp_path):
        result = dedup_store.load(str(tmp_path / "nope.json"))
        assert result == set()

    def test_load_existing(self, tmp_path):
        path = tmp_path / "processed.json"
        path.write_text('["abc", "def"]')
        result = dedup_store.load(str(path))
        assert result == {"abc", "def"}

    def test_roundtrip(self, tmp_path):
        path = tmp_path / "processed.json"
        ids = {"msg1", "msg2", "msg3"}
        dedup_store.save(ids, str(path))
        loaded = dedup_store.load(str(path))
        assert loaded == ids

    def test_save_sorted(self, tmp_path):
        path = tmp_path / "processed.json"
        dedup_store.save({"c", "a", "b"}, str(path))
        data = json.loads(path.read_text())
        assert data == ["a", "b", "c"]

    def test_is_processed_true(self):
        ids = {"msg1", "msg2"}
        assert dedup_store.is_processed(ids, "msg1") is True

    def test_is_processed_false(self):
        ids = {"msg1", "msg2"}
        assert dedup_store.is_processed(ids, "msg3") is False

    def test_mark_processed(self, monkeypatch):
        monkeypatch.setattr(dedup_store, "save", lambda ids, *a: None)
        ids = {"msg1"}
        dedup_store.mark_processed(ids, "msg2")
        assert "msg2" in ids

    def test_mark_saves_to_disk(self, tmp_path, monkeypatch):
        path = tmp_path / "processed.json"
        monkeypatch.setattr(dedup_store, "save", lambda ids, p=str(path): _save_to(ids, p))
        ids = set()
        dedup_store.mark_processed(ids, "abc")
        data = json.loads(path.read_text())
        assert "abc" in data


def _save_to(ids, path):
    """Helper to save to a specific path."""
    import json
    with open(path, "w") as f:
        json.dump(sorted(ids), f, indent=2)
        f.write("\n")
