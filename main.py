#!/usr/bin/env python3
"""
Expense Agent — Capital One / Venmo Email Parser

Usage:
    expense --gmail               # read unread emails from Gmail
    expense --seed                # bootstrap categories.json from Excel
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from rich.console import Console

import category_store
import display
import email_reader
import excel_writer
import parser as expense_parser
import splitter

console = Console()

# Resolve project root so `expense` works from any directory
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config(path: str = "config.json") -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        display.print_error(
            f"config.json not found. Create it with 'excel_path' and 'sheet_name'.\n"
            "See config.json.example for the expected format."
        )
        sys.exit(1)
    except json.JSONDecodeError as exc:
        display.print_error(f"config.json is not valid JSON: {exc}")
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Parse financial email notifications and log them to Excel."
    )
    p.add_argument(
        "--gmail",
        action="store_true",
        help="Fetch unread emails from Gmail and process each one",
    )
    p.add_argument(
        "--seed",
        action="store_true",
        help="Bootstrap categories.json from existing Excel data, then exit",
    )
    return p.parse_args()


def seed_categories(config: dict) -> None:
    """Read all rows from Excel and write the item→category mapping to categories.json."""
    display.print_info("Reading all rows from Excel...")
    mapping = excel_writer.read_all_categories(config)
    if not mapping:
        display.print_error("No data found in the Excel sheet.")
        sys.exit(1)
    category_store.save(mapping)
    display.print_info(f"Wrote {len(mapping)} entries to categories.json")


def process_email(email_text: str, config: dict, categories: dict) -> bool:
    """
    Run the full processing pipeline on a single email.

    Returns True if the transaction was written to Excel, False otherwise.
    """
    if not email_text.strip():
        display.print_error("Empty email text — skipping.")
        return False

    # Detect source
    source = email_reader.detect_source(email_text)
    if source != "unknown":
        display.print_info(f"Detected source: {source}")

    # Parse with Claude
    display.print_info("Parsing with Claude...")
    try:
        transaction = expense_parser.parse_transaction(email_text, source, config)
    except expense_parser.ParsingError as exc:
        display.print_error(str(exc))
        return False

    # Local category override for known merchants
    stored_category = category_store.lookup(categories, transaction["item"])
    if stored_category:
        transaction["category"] = stored_category

    # Action loop: show preview, let user write/split/edit/skip
    while True:
        display.show_compact(transaction)
        action = display.prompt_action()

        if action == "write":
            try:
                excel_writer.append_row(config, transaction)
                display.print_success(config["sheet_name"], config["excel_path"])
            except excel_writer.ExcelError as exc:
                display.print_error(str(exc))
                return False

            categories[transaction["item"]] = transaction["category"]
            category_store.save(categories)
            return True

        if action == "split":
            transaction["amount"] = splitter.prompt_split(transaction["amount"])

        elif action == "edit":
            display.prompt_edit(transaction)

        elif action == "skip":
            display.print_cancelled()
            return False


def run_gmail(config: dict, categories: dict) -> None:
    """Fetch unread emails from Gmail and process each one."""
    import gmail_reader

    display.print_info("Fetching unread emails from Gmail...")
    try:
        emails = gmail_reader.fetch_unread_emails()
    except FileNotFoundError as exc:
        display.print_error(str(exc))
        sys.exit(1)

    if not emails:
        display.print_info("No unread emails found.")
        return

    console.print(f"\n[bold]Found {len(emails)} unread email(s).[/bold]\n")

    for i, (msg_id, email_text) in enumerate(emails, start=1):
        console.print(f"\n[bold cyan]── Email {i}/{len(emails)} ──[/bold cyan]")
        written = process_email(email_text, config, categories)

        if written:
            gmail_reader.mark_as_read(msg_id)
            display.print_info("Marked as read in Gmail.")
        else:
            display.print_info("Skipped — email left unread in Gmail.")

    console.print(f"\n[bold green]Done processing {len(emails)} email(s).[/bold green]\n")


def main() -> None:
    os.chdir(PROJECT_DIR)
    load_dotenv()

    args = parse_args()
    config = load_config("config.json")

    # Handle --seed: bootstrap categories.json and exit
    if args.seed:
        seed_categories(config)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        display.print_error(
            "ANTHROPIC_API_KEY is not set.\n"
            "Create a .env file with: ANTHROPIC_API_KEY=sk-ant-..."
        )
        sys.exit(1)

    console.print("\n[bold cyan]Expense Agent[/bold cyan] — Financial Email Parser")
    console.print("─" * 50)

    # Load local category lookup
    categories = category_store.load()

    if args.gmail:
        run_gmail(config, categories)
    else:
        display.print_error("No mode specified. Use: expense --gmail or expense --seed")
        sys.exit(1)


if __name__ == "__main__":
    main()
