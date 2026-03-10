"""Tests for splitter.py — _parse_custom_split."""

import pytest
from splitter import _parse_custom_split


class TestParseCustomSplit:
    def test_dollar_amount(self):
        assert _parse_custom_split("8.50", 20.00) == 8.50

    def test_percentage(self):
        assert _parse_custom_split("50%", 20.00) == 10.00

    def test_percentage_rounding(self):
        result = _parse_custom_split("33%", 10.00)
        assert result == 3.30

    def test_100_percent(self):
        assert _parse_custom_split("100%", 25.00) == 25.00

    def test_zero_percent_raises(self):
        with pytest.raises(ValueError):
            _parse_custom_split("0%", 20.00)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            _parse_custom_split("-5", 20.00)

    def test_exceeds_full_allowed(self):
        assert _parse_custom_split("25.00", 20.00) == 25.00

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _parse_custom_split("", 20.00)

    def test_garbage_raises(self):
        with pytest.raises(ValueError):
            _parse_custom_split("abc", 20.00)

    def test_invalid_percent_raises(self):
        with pytest.raises(ValueError):
            _parse_custom_split("abc%", 20.00)

    def test_over_100_percent_allowed(self):
        assert _parse_custom_split("150%", 20.00) == 30.00
