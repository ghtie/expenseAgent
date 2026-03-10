"""Tests for email_reader.py — detect_source and read_from_file."""

import pytest
from email_reader import detect_source, read_from_file


# ---------- detect_source ----------

class TestDetectSource:
    def test_capitalone_by_name(self):
        assert detect_source("Your Capital One account alert") == "capitalone"

    def test_capitalone_by_domain(self):
        assert detect_source("From: alerts@capitalone.com") == "capitalone"

    def test_venmo_by_name(self):
        assert detect_source("Venmo payment received") == "venmo"

    def test_venmo_by_domain(self):
        assert detect_source("From: no-reply@venmo.com") == "venmo"

    def test_unknown(self):
        assert detect_source("Hello from your bank") == "unknown"

    def test_case_insensitive(self):
        assert detect_source("CAPITAL ONE alert") == "capitalone"


# ---------- read_from_file ----------

class TestReadFromFile:
    def test_read_txt(self, tmp_path):
        f = tmp_path / "email.txt"
        f.write_text("Hello world")
        assert read_from_file(str(f)) == "Hello world"

    def test_read_eml(self, tmp_path):
        eml_content = (
            "From: test@example.com\n"
            "To: user@example.com\n"
            "Subject: Test\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=utf-8\n"
            "\n"
            "This is the body.\n"
        )
        f = tmp_path / "email.eml"
        f.write_text(eml_content)
        result = read_from_file(str(f))
        assert "This is the body." in result

    def test_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_from_file(str(tmp_path / "nope.txt"))
