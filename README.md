# Expense Agent

A Python CLI tool that parses financial email notifications (Capital One, Venmo) and logs transactions to an Excel spreadsheet using Claude AI for extraction and categorization.

## Features

- **Auto-detection** of Capital One and Venmo email formats
- **AI-powered categorization** into 24 predefined expense categories
- **Local category lookup** — known merchants are categorized instantly from a local `categories.json` file, skipping the API call for categorization
- **Smart item naming** — merchant names are stripped down to their core brand name with proper capitalization (e.g. "UBER EATS" → "Uber Eats")
- **Expense splitting** — full amount, 50/50, or custom split by dollar amount or percentage
- **Interactive corrections** — preview and edit item name or category before saving
- **Formatted Excel output** — currency formatting, date formatting, and cell alignment matching your existing spreadsheet

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

3. Create a `config.json` file:
   ```json
   {
     "excel_path": "/path/to/your/Budget.xlsx",
     "sheet_name": "Daily Expenses",
     "model": "claude-opus-4-6"
   }
   ```
   Your Excel sheet should have columns: Year (A), Month (B), Date (C), Amount (D), Category (E), Item (F).

4. (Optional) Seed the local category lookup from your existing spreadsheet:
   ```bash
   python main.py --seed
   ```
   This reads all rows from your Excel sheet and writes the merchant→category mappings to `categories.json`. Only needed once — after that, new mappings are saved automatically as you confirm transactions.

## Usage

```bash
# From a text file
python main.py --file email.txt

# From an .eml file
python main.py --file email.eml

# Paste mode (paste email text, then type END on a new line)
python main.py

# Bootstrap categories.json from existing Excel data
python main.py --seed
```

## How It Works

1. Email is parsed by Claude to extract date, amount, item, and category
2. The item is checked against `categories.json` for a known category
   - **Found** → the stored category is used (no API categorization needed)
   - **Not found** → Claude's category is used (new merchant)
3. You preview, optionally correct, and confirm the transaction
4. The row is written to Excel and the item→category mapping is saved to `categories.json`

## Supported Categories

Apartment Necessities, Clothing & Shoes, Education, Electricity, Entertainment, Essentials, Food & Dining, Gift, Groceries, Health, Hobbies, Misc, Phone, School, Skincare & Makeup, Special Events, Subscriptions, Transportation, Travel - Flight, Travel - Food & Dining, Travel - Hotel, Travel - Misc, Travel - Special Events, Travel - Transportation, Utilities

## Adding a New Email Source

1. Add a detection rule in `email_reader.detect_source()`
2. Add a prompt template in `parser.SOURCE_PROMPTS` with the same key
