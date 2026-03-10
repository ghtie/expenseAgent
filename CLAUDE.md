# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Python CLI tool (`expense`) that fetches Capital One and Venmo transaction emails from Gmail, parses them with regex, and logs expenses to an Excel spreadsheet. No AI/LLM APIs — pure regex parsing.

## Commands

```bash
# Install as editable CLI tool
pip install -e .

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_parser.py -v

# Run a single test class or method
python -m pytest tests/test_parser.py::TestCleanMerchant::test_clean_sq_prefix -v

# CLI usage
expense --gmail      # fetch and process unread emails
expense --seed       # bootstrap categories.json from Excel
expense --undo       # remove last written row
```

## Architecture

**Entry point:** `main.py` → `main()` dispatches to `run_gmail()`, `seed_categories()`, or `run_undo()`.

**Pipeline flow (--gmail):**
1. `gmail_reader` fetches unread emails via Gmail API
2. `parser.detect_source()` identifies email type via the `PARSERS` registry
3. `parser.parse_transaction()` dispatches to `parse_capitalone()` or `parse_venmo()` regex extractors
4. `merchant_store` / `category_store` auto-resolve item names and categories
5. `display` renders Rich tables and handles interactive edit/split/skip/write prompts
6. `excel_writer` appends confirmed rows to the .xlsx file
7. `dedup_store` tracks processed Gmail message IDs to prevent re-processing

**Shared utilities (avoid duplicating logic in stores/parser):**
- `merchant_utils.normalize_merchant()` — single source of truth for merchant name cleaning (used by both `parser._clean_merchant()` and `merchant_store.derive_key()`)
- `json_store.load_json()` / `save_json()` — shared JSON file I/O (used by `category_store`, `merchant_store`, `dedup_store`)
- `lookup_utils.longest_substring_match()` — shared fuzzy matching (used by `category_store.lookup()` with `bidirectional=True`, `merchant_store.lookup()` with `bidirectional=False`)

**Parser registry pattern:** `parser.PARSERS` is a dict mapping source name → `{"detect": fn, "parse": fn}`. To add a new email source, add one entry to this dict — no other files need editing. `email_reader.detect_source()` delegates to `parser.detect_source()`.

**`run_gmail()` decomposition:** Orchestrates three private functions: `_fetch_and_parse()` (Gmail fetch + dedup + parse), `_run_batch_loop()` (interactive UI loop), `_print_summary()` (final table + totals).

## Key Conventions

- All modules are flat in the project root (no `src/` directory). `pyproject.toml` lists them explicitly in `py-modules`.
- Transactions are plain dicts with keys: `date` (MM/DD/YYYY string), `item`, `category`, `amount` (float). `_raw_merchant` is internal metadata stripped before display.
- JSON data files (`categories.json`, `merchants.json`, `processed.json`) live in the project root alongside code. They are runtime data, not checked into git.
- `config.json` holds `excel_path` and `sheet_name`. `credentials.json` and `token.json` are for Gmail OAuth.
- Tests use `conftest.py` fixtures (`sample_capitalone_email`, `sample_venmo_subject`, `sample_venmo_body`, `config`, `sample_categories`, `sample_merchants`).
- `display.py` owns the shared `Console` instance. `splitter.py` imports it as `from display import console`.
- Excel columns: Year (A), Month (B), Date (C), Amount (D), Category (E), Item (F).
- The splitter allows amounts exceeding the original and percentages over 100%.
