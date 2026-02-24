#!/usr/bin/env python3
"""
Expense Agent — Capital One / Venmo Email Parser

Usage:
    python main.py                       # paste mode
    python main.py --file email.txt      # plain-text file
    python main.py --file email.eml      # .eml file
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from rich.console import Console

import display
import email_reader
import excel_writer
import parser as expense_parser
import splitter

console = Console()


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
        description="Parse a financial email notification and log it to Excel."
    )
    p.add_argument(
        "--file", "-f",
        metavar="PATH",
        help="Path to a .txt or .eml email file (omit for paste mode)",
    )
    return p.parse_args()


def main() -> None:
    load_dotenv()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        display.print_error(
            "ANTHROPIC_API_KEY is not set.\n"
            "Create a .env file with: ANTHROPIC_API_KEY=sk-ant-..."
        )
        sys.exit(1)

    args = parse_args()
    config = load_config("config.json")

    console.print("\n[bold cyan]Expense Agent[/bold cyan] — Financial Email Parser")
    console.print("─" * 50)

    # Step 1: Read email text
    try:
        if args.file:
            display.print_info(f"Reading from file: {args.file}")
        email_text = email_reader.get_email_text(args.file)
    except FileNotFoundError as exc:
        display.print_error(str(exc))
        sys.exit(1)

    if not email_text.strip():
        display.print_error("No email text was provided.")
        sys.exit(1)

    # Step 2: Detect source
    source = email_reader.detect_source(email_text)
    if source != "unknown":
        display.print_info(f"Detected email source: {source}")

    # Step 3: Parse and categorize with Claude
    history = excel_writer.read_recent_rows(config)
    display.print_info("Parsing transaction with Claude...\n")
    try:
        transaction = expense_parser.parse_transaction(email_text, source, config, history=history)
    except expense_parser.ParsingError as exc:
        display.print_error(str(exc))
        sys.exit(1)

    # Step 4: Handle split
    transaction["amount"] = splitter.prompt_split(transaction["amount"])

    # Step 5: Preview + optional corrections
    display.show_preview(transaction)
    if display.ask_corrections(transaction):
        display.show_preview(transaction)

    # Step 6: Confirm and write
    if display.ask_confirm():
        try:
            excel_writer.append_row(config, transaction)
            display.print_success(config["sheet_name"], config["excel_path"])
        except excel_writer.ExcelError as exc:
            display.print_error(str(exc))
            sys.exit(1)
    else:
        display.print_cancelled()


if __name__ == "__main__":
    main()
