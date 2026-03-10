"""Tests for merchant_utils.py — shared merchant normalization."""

from expense_agent.utils.merchant_utils import normalize_merchant


class TestNormalizeMerchant:
    def test_www_dot_com(self):
        assert normalize_merchant("WWW.CSCSW.COM") == "cscsw"

    def test_sq_prefix(self):
        assert normalize_merchant("SQ *DELICA") == "delica"

    def test_tst_prefix(self):
        assert normalize_merchant("TST* BLUE BOTTLE") == "blue bottle"

    def test_pp_prefix(self):
        assert normalize_merchant("PP*SPOTIFY") == "spotify"

    def test_store_number(self):
        assert normalize_merchant("NIJIYA MARKET #62") == "nijiya market"

    def test_trader_joes(self):
        assert normalize_merchant("TRADER JOE S #123") == "trader joe"

    def test_location_suffix(self):
        assert normalize_merchant("DAISO - JAPAN TOWN") == "daiso"

    def test_trailing_digits(self):
        assert normalize_merchant("WALGREENS 12345") == "walgreens"

    def test_newlines(self):
        assert normalize_merchant("SOME\nMERCHANT") == "some merchant"

    def test_already_clean(self):
        assert normalize_merchant("Whole Foods") == "whole foods"
