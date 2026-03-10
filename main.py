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

from rich.console import Console

import category_store
import dedup_store
import display
import email_reader
import excel_writer
import merchant_store
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
    p.add_argument(
        "--undo",
        action="store_true",
        help="Remove the last row written to Excel",
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


def _parse_email(email_text: str, subject: str, categories: dict, merchants: dict) -> dict | None:
    """
    Parse a single email into a transaction dict.
    Returns None if unparseable. Adds '_raw_merchant' and '_msg_id' metadata.
    """
    if not email_text.strip():
        return None

    source = expense_parser.detect_source(email_text)
    if source == "unknown":
        return None

    try:
        txn = expense_parser.parse_transaction(email_text, source, subject)
    except expense_parser.ParsingError as exc:
        display.print_error(str(exc))
        return None

    raw_merchant = txn.pop("_raw_merchant", "")

    # Merchant auto-learn lookup (provides both name + category)
    merchant_match = merchant_store.lookup(merchants, raw_merchant)
    if merchant_match:
        txn["item"] = merchant_match["name"]
        txn["category"] = merchant_match["category"]
    else:
        # Fall back to category-only lookup
        stored_category = category_store.lookup(categories, txn["item"])
        if stored_category:
            txn["category"] = stored_category

    txn["_raw_merchant"] = raw_merchant
    return txn


def _write_transaction(config: dict, txn: dict, raw_merchant: str,
                       categories: dict, merchants: dict,
                       processed_ids: set = None, msg_id: str = "") -> bool:
    """Write a single transaction to Excel and update lookup stores."""
    try:
        excel_writer.append_row(config, txn)
    except excel_writer.ExcelError as exc:
        display.print_error(str(exc))
        return False

    # Update categories.json
    categories[txn["item"]] = txn["category"]
    category_store.save(categories)

    # Update merchants.json
    if raw_merchant:
        merchant_store.learn(merchants, raw_merchant, txn["item"], txn["category"])

    # Track as processed for dedup
    if processed_ids is not None and msg_id:
        dedup_store.mark_processed(processed_ids, msg_id)

    return True


def run_undo(config: dict) -> None:
    """Remove the last row from Excel."""
    try:
        removed = excel_writer.remove_last_row(config)
    except excel_writer.ExcelError as exc:
        display.print_error(str(exc))
        sys.exit(1)

    if removed is None:
        display.print_info("No rows to undo.")
        return

    display.print_info("Removed last row:")
    display.show_compact(removed)


def _fetch_and_parse(config, categories, merchants):
    """Fetch emails from Gmail, filter duplicates, and parse into entries.

    Returns (entries, processed_ids) where entries is a list of
    {"msg_id", "transaction", "raw_merchant"} dicts.
    """
    import gmail_reader

    display.print_info("Fetching unread emails from Gmail...")
    query = config.get("gmail_query")
    try:
        emails = gmail_reader.fetch_unread_emails(query) if query else gmail_reader.fetch_unread_emails()
    except FileNotFoundError as exc:
        display.print_error(str(exc))
        sys.exit(1)

    if not emails:
        display.print_info("No unread emails found.")
        return [], set()

    processed_ids = dedup_store.load()
    console.print(f"\n[bold]Found {len(emails)} unread email(s).[/bold]")

    entries = []
    skipped_dedup = 0
    for msg_id, subject, email_text in emails:
        if dedup_store.is_processed(processed_ids, msg_id):
            skipped_dedup += 1
            continue
        txn = _parse_email(email_text, subject, categories, merchants)
        if txn is None:
            display.print_info(f"Could not parse email: {subject[:60]}")
            continue
        raw_merchant = txn.pop("_raw_merchant", "")
        entries.append({
            "msg_id": msg_id,
            "transaction": txn,
            "raw_merchant": raw_merchant,
        })

    if skipped_dedup:
        display.print_info(f"Skipped {skipped_dedup} already-processed email(s).")

    return entries, processed_ids


def _run_batch_loop(config, entries, categories, merchants, processed_ids):
    """Run the interactive batch edit/split/skip/write loop.

    Returns a list of status strings parallel to entries.
    """
    import gmail_reader

    transactions = [e["transaction"] for e in entries]
    statuses = ["pending"] * len(entries)

    display.show_batch_table(transactions, statuses)

    while True:
        pending = [i for i, s in enumerate(statuses) if s == "pending"]
        if not pending:
            break

        action, indices = display.prompt_batch_action(len(entries))

        if action == "all":
            for i in pending:
                ok = _write_transaction(
                    config, transactions[i], entries[i]["raw_merchant"],
                    categories, merchants, processed_ids, entries[i]["msg_id"],
                )
                if ok:
                    statuses[i] = "written"
                    gmail_reader.mark_as_read(entries[i]["msg_id"])
                else:
                    statuses[i] = "error"
            break

        elif action == "skip":
            for idx in indices:
                if statuses[idx] not in ("pending", "error"):
                    display.print_info(f"Item #{idx + 1} is already {statuses[idx]}.")
                else:
                    statuses[idx] = "skipped"
            display.show_batch_table(transactions, statuses)

        elif action == "edit":
            for idx in indices:
                if statuses[idx] not in ("pending", "error"):
                    display.print_info(f"Item #{idx + 1} is already {statuses[idx]}.")
                    continue
                console.print(f"\n[bold cyan]── Editing #{idx + 1} ──[/bold cyan]")
                display.show_compact(transactions[idx])
                display.prompt_edit(transactions[idx])
            display.show_batch_table(transactions, statuses)

        elif action == "split":
            for idx in indices:
                if statuses[idx] not in ("pending", "error"):
                    display.print_info(f"Item #{idx + 1} is already {statuses[idx]}.")
                    continue
                console.print(f"\n[bold cyan]── Splitting #{idx + 1} ──[/bold cyan]")
                display.show_compact(transactions[idx])
                transactions[idx]["amount"] = splitter.prompt_split(transactions[idx]["amount"])
            display.show_batch_table(transactions, statuses)

    return statuses


def _print_summary(transactions, statuses):
    """Display the final batch table with totals."""
    written_count = statuses.count("written")
    skipped_count = statuses.count("skipped")
    error_count = statuses.count("error")

    display.show_batch_table(transactions, statuses)

    parts = [f"{written_count} written"]
    if skipped_count:
        parts.append(f"{skipped_count} skipped")
    if error_count:
        parts.append(f"{error_count} failed")

    total_amount = sum(
        t["amount"] for t, s in zip(transactions, statuses) if s == "written"
    )
    console.print(
        f"\n[bold green]Done: {', '.join(parts)}. "
        f"Total: ${total_amount:.2f}[/bold green]\n"
    )


def run_gmail(config: dict, categories: dict, merchants: dict) -> None:
    """Fetch unread emails from Gmail and process in batch mode."""
    entries, processed_ids = _fetch_and_parse(config, categories, merchants)

    if not entries:
        return

    statuses = _run_batch_loop(config, entries, categories, merchants, processed_ids)
    transactions = [e["transaction"] for e in entries]
    _print_summary(transactions, statuses)


def main() -> None:
    os.chdir(PROJECT_DIR)

    args = parse_args()
    config = load_config("config.json")

    # Handle --seed: bootstrap categories.json and exit
    if args.seed:
        seed_categories(config)
        return

    # Handle --undo: remove last row and exit
    if args.undo:
        run_undo(config)
        return

    console.print("\n[bold cyan]Expense Agent[/bold cyan] — Financial Email Parser")
    console.print("─" * 50)

    # Load local lookups
    categories = category_store.load()
    merchants = merchant_store.load()

    if args.gmail:
        run_gmail(config, categories, merchants)
    else:
        display.print_error("No mode specified. Use: expense --gmail, expense --seed, or expense --undo")
        sys.exit(1)


if __name__ == "__main__":
    main()
