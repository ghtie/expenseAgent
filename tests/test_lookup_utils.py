"""Tests for lookup_utils.py — shared fuzzy matching."""

from expense_agent.utils.lookup_utils import longest_substring_match


class TestLongestSubstringMatch:
    def test_exact_substring(self):
        keys = {"trader joe": "v", "target": "v"}
        assert longest_substring_match("trader joe s", keys) == "trader joe"

    def test_longest_wins(self):
        keys = {"blue": "v", "blue bottle": "v"}
        assert longest_substring_match("blue bottle coffee", keys) == "blue bottle"

    def test_no_match(self):
        keys = {"trader joe": "v"}
        assert longest_substring_match("walgreens", keys) is None

    def test_min_len_filter(self):
        keys = {"ab": "v", "abc": "v"}
        assert longest_substring_match("xabcx", keys) == "abc"
        assert longest_substring_match("xabx", keys) is None

    def test_bidirectional_false(self):
        keys = {"blue bottle coffee shop": "v"}
        # query is shorter than key, should not match without bidirectional
        assert longest_substring_match("blue bottle", keys, bidirectional=False) is None

    def test_bidirectional_true(self):
        keys = {"blue bottle coffee shop": "v"}
        assert longest_substring_match("blue bottle", keys, bidirectional=True) == "blue bottle coffee shop"

    def test_empty_keys(self):
        assert longest_substring_match("anything", {}) is None
