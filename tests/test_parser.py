"""Tests for parser.py — date parsing, merchant cleaning, and email parsing."""

import pytest
from parser import _parse_date, _clean_merchant, parse_capitalone, parse_venmo, parse_transaction, ParsingError


# ---------- _parse_date ----------

class TestParseDate:
    def test_full_month(self):
        assert _parse_date("February 19, 2026") == "02/19/2026"

    def test_abbreviated(self):
        assert _parse_date("Feb 19, 2026") == "02/19/2026"

    def test_single_digit_day(self):
        assert _parse_date("March 3, 2026") == "03/03/2026"

    def test_with_whitespace(self):
        assert _parse_date("  February 19, 2026  ") == "02/19/2026"

    def test_invalid_raises(self):
        with pytest.raises(ParsingError):
            _parse_date("19 Feb 2026")

    def test_garbage_raises(self):
        with pytest.raises(ParsingError):
            _parse_date("not a date")


# ---------- _clean_merchant ----------

class TestCleanMerchant:
    def test_clean_www_dot_com(self):
        assert _clean_merchant("WWW.CSCSW.COM") == "Cscsw"

    def test_clean_sq_prefix(self):
        assert _clean_merchant("SQ *DELICA") == "Delica"

    def test_clean_tst_prefix(self):
        assert _clean_merchant("TST* BLUE BOTTLE") == "Blue Bottle"

    def test_clean_pp_prefix(self):
        assert _clean_merchant("PP*SPOTIFY") == "Spotify"

    def test_clean_store_number(self):
        assert _clean_merchant("NIJIYA MARKET #62") == "Nijiya Market"

    def test_clean_trader_joes(self):
        result = _clean_merchant("TRADER JOE S #123")
        assert result == "Trader Joe"

    def test_clean_target_code(self):
        result = _clean_merchant("TARGET T-")
        assert result == "Target"

    def test_clean_location_suffix(self):
        assert _clean_merchant("DAISO - JAPAN TOWN") == "Daiso"

    def test_clean_ups(self):
        result = _clean_merchant("UPS*INTERNETSHIPWAYBIL")
        # Should be title-cased
        assert result == result.title()
        assert result[0].isupper()

    def test_clean_trailing_digits(self):
        assert _clean_merchant("WALGREENS 12345") == "Walgreens"

    def test_clean_newlines(self):
        assert _clean_merchant("SOME\nMERCHANT") == "Some Merchant"

    def test_clean_already_clean(self):
        assert _clean_merchant("Whole Foods") == "Whole Foods"


# ---------- parse_capitalone ----------

class TestParseCapitalone:
    def test_sample_file(self, sample_capitalone_email):
        result = parse_capitalone(sample_capitalone_email)
        assert result["date"] == "02/21/2026"
        assert result["item"] == "Cscsw"
        assert result["amount"] == 5.25

    def test_primary_pattern(self):
        email = (
            "on March 10, 2026, at\n"
            "TRADER JOE S #123, a pending authorization or purchase "
            "in the amount of $42.99\n"
            "was placed on your card."
        )
        result = parse_capitalone(email)
        assert result["date"] == "03/10/2026"
        assert result["item"] == "Trader Joe"
        assert result["amount"] == 42.99

    def test_fallback_pattern(self):
        email = (
            "On January 5, 2026, "
            "at SQ *DELICA, a purchase "
            "was charged in the amount of $15.00."
        )
        result = parse_capitalone(email)
        assert result["date"] == "01/05/2026"
        assert result["amount"] == 15.00

    def test_multiline_merchant(self):
        email = (
            "on February 21, 2026, at\n"
            "SOME\nMERCHANT, a pending authorization or purchase "
            "in the amount of $10.00\n"
            "was placed on your card."
        )
        result = parse_capitalone(email)
        assert result["item"] == "Some Merchant"

    def test_comma_amount(self):
        email = (
            "on February 21, 2026, at\n"
            "BIG STORE, a pending authorization or purchase "
            "in the amount of $1,234.56\n"
            "was placed on your card."
        )
        result = parse_capitalone(email)
        assert result["amount"] == 1234.56

    def test_no_match_raises(self):
        with pytest.raises(ParsingError):
            parse_capitalone("this is not an email")

    def test_returns_raw_merchant(self, sample_capitalone_email):
        result = parse_capitalone(sample_capitalone_email)
        assert "_raw_merchant" in result
        assert "CSCSW" in result["_raw_merchant"]


# ---------- parse_venmo ----------

class TestParseVenmo:
    def test_with_note(self, sample_venmo_subject, sample_venmo_body):
        result = parse_venmo(sample_venmo_body, sample_venmo_subject)
        assert result["item"] == "Dinner split"

    def test_without_note(self, sample_venmo_subject):
        body = (
            "Someone paid you\n"
            "$10.31\n"
            "Date\n"
            "Feb 19, 2026\n"
        )
        result = parse_venmo(body, sample_venmo_subject)
        assert result["item"] == "Venmo Payment"

    def test_amount_from_subject(self, sample_venmo_subject, sample_venmo_body):
        result = parse_venmo(sample_venmo_body, sample_venmo_subject)
        assert result["amount"] == 10.31

    def test_missing_amount_raises(self, sample_venmo_body):
        with pytest.raises(ParsingError):
            parse_venmo(sample_venmo_body, "Some random subject")

    def test_missing_date_raises(self, sample_venmo_subject):
        body = "Jeffrey He paid you\n$10.31\nDinner\nSee transaction details\n"
        with pytest.raises(ParsingError):
            parse_venmo(body, sample_venmo_subject)

    def test_comma_amount(self):
        subject = "Someone paid your $1,000.00 request"
        body = (
            "Someone paid you\n"
            "$1,000.00\n"
            "Date\n"
            "Mar 1, 2026\n"
        )
        result = parse_venmo(body, subject)
        assert result["amount"] == 1000.00


# ---------- parse_transaction ----------

class TestParseTransaction:
    def test_dispatch_capitalone(self, sample_capitalone_email):
        result = parse_transaction(sample_capitalone_email, "capitalone")
        assert result["date"] == "02/21/2026"

    def test_dispatch_venmo(self, sample_venmo_subject, sample_venmo_body):
        result = parse_transaction(sample_venmo_body, "venmo", sample_venmo_subject)
        assert result["amount"] == 10.31

    def test_unknown_source_raises(self):
        with pytest.raises(ParsingError):
            parse_transaction("text", "amex")
