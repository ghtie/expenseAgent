# Expense Agent

A Python CLI tool that reads transaction emails from Gmail (Capital One, Venmo) and logs expenses to an Excel spreadsheet. Uses regex-based parsing — no API keys or AI costs.

## Features

- **Gmail integration** — fetches unread transaction emails directly from a dedicated Gmail inbox
- **Auto-detection** of Capital One and Venmo email formats
- **Regex parsing** — extracts date, merchant, and amount with zero API costs
- **Local category lookup** — known merchants are categorized from `categories.json`
- **Category picker** — numbered menu of 25 expense categories for quick selection
- **Expense splitting** — full amount, 50/50, or custom split by dollar amount or percentage
- **Compact interactive flow** — one-line preview with `[w]rite / [s]plit / [e]dit / [sk]ip`
- **Auto mark-as-read** — processed emails are marked as read in Gmail

## Setup

1. Install as a CLI tool:
   ```bash
   pip install -e .
   ```

2. Create a `config.json` file:
   ```json
   {
     "excel_path": "/path/to/your/Budget.xlsx",
     "sheet_name": "Daily Expenses"
   }
   ```
   Your Excel sheet should have columns: Year (A), Month (B), Date (C), Amount (D), Category (E), Item (F).

3. Set up Gmail API access — see [GMAIL_SETUP.md](GMAIL_SETUP.md) for full instructions.

4. (Optional) Seed the local category lookup from your existing spreadsheet:
   ```bash
   expense --seed
   ```
   This reads all rows from your Excel sheet and writes the merchant→category mappings to `categories.json`. Only needed once — new mappings are saved automatically as you confirm transactions.

## Usage

```bash
# Fetch and process unread emails from Gmail
expense --gmail

# Bootstrap categories.json from existing Excel data
expense --seed
```

## How It Works

1. Unread emails are fetched from Gmail
2. Each email is detected as Capital One or Venmo and parsed with regex
3. The merchant is checked against `categories.json` for a known category
4. You review each transaction and choose to write, split, edit, or skip
5. Confirmed rows are written to Excel, the email is marked as read, and the merchant→category mapping is saved

## Adding a New Email Source

1. Add a detection rule in `email_reader.detect_source()`
2. Add a regex parser function in `parser.py`
3. Add the source to `parse_transaction()` dispatch
