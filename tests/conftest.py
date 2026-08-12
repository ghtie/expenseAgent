"""Shared fixtures for the expense agent test suite."""

import pytest
import openpyxl
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_capitalone_email():
    """Return text from the real Capital One sample email."""
    return (PROJECT_ROOT / "sample_emails" / "capitalone_sample.txt").read_text()


@pytest.fixture
def sample_venmo_subject():
    """Venmo subject line matching the parser's expected format."""
    return "Jeffrey He paid your $10.31 request"


@pytest.fixture
def sample_venmo_body():
    """Venmo email body matching the parser's expected regex patterns."""
    return (
        "Jeffrey He paid you\n"
        "$10.31\n"
        "Dinner split\n"
        "See transaction details\n"
        "\n"
        "Date\n"
        "Feb 19, 2026\n"
    )


@pytest.fixture
def config(tmp_path):
    """Create a real .xlsx with a 'Daily Expenses' sheet and return config dict."""
    excel_path = tmp_path / "budget.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Daily Expenses"
    # Add a header row so max_row starts at 1
    ws.append(["Year", "Month", "Date", "Amount", "Category", "Subcategory", "Item"])
    wb.save(excel_path)
    return {
        "excel_path": str(excel_path),
        "sheet_name": "Daily Expenses",
    }


@pytest.fixture
def sample_bofa_body():
    """Bank of America alert email body (after HTML stripping)."""
    return (
        "Bank of America.\n"
        "Credit card transaction\n"
        "Cash Rewards Visa ending in 2221\n"
        "Amount:\n$59.08\n"
        "Date:\nAugust 11, 2026\n"
        "Where:\nWEEE INC.\n"
        "If you made this purchase or payment but don't recognize the amount, "
        "wait until the final purchase amount has posted before filing a dispute claim.\n"
    )


@pytest.fixture
def sample_categories():
    return {
        "Trader Joes": "Groceries",
        "Target": "Essentials",
        "Delica": "Food & Dining",
    }


@pytest.fixture
def sample_merchants():
    return {
        "trader joe": {"name": "Trader Joes", "subcategory": "Groceries"},
    }
