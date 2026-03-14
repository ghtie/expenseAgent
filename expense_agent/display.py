from rich.console import Console
from rich.table import Table

console = Console()

CATEGORIES = [
    "Apartment Necessities",
    "Clothing & Shoes",
    "Education",
    "Electricity",
    "Entertainment",
    "Essentials",
    "Food & Dining",
    "Gift",
    "Groceries",
    "Health",
    "Hobbies",
    "Misc",
    "Phone",
    "School",
    "Skincare & Makeup",
    "Special Events",
    "Subscriptions",
    "Transportation",
    "Travel - Flight",
    "Travel - Food & Dining",
    "Travel - Hotel",
    "Travel - Misc",
    "Travel - Special Events",
    "Travel - Transportation",
    "Utilities",
]


def show_compact(transaction: dict) -> None:
    """Print a one-line summary of the transaction."""
    console.print(
        f"  [dim]Date:[/dim] {transaction['date']}  "
        f"[dim]Category:[/dim] {transaction['category']}  "
        f"[dim]Item:[/dim] {transaction['item']}  "
        f"[dim]Amount:[/dim] [green]${transaction['amount']:.2f}[/green]"
    )


def prompt_action() -> str:
    """
    Show the action menu and return the user's choice.

    Returns one of: "write", "split", "edit", "skip"
    """
    while True:
        choice = console.input(
            "  [bold]\\[w]rite[/bold] / \\[s]plit / \\[e]dit / \\[sk]ip "
            "[[bold]default: w[/bold]]: "
        ).strip().lower()

        if choice in ("", "w", "write"):
            return "write"
        if choice in ("s", "split"):
            return "split"
        if choice in ("e", "edit"):
            return "edit"
        if choice in ("sk", "skip"):
            return "skip"

        console.print("  [red]Enter w, s, e, or sk[/red]")


def prompt_edit(transaction: dict) -> None:
    """Prompt for item, category, and amount edits. Modifies transaction in place."""
    new_item = console.input(f"  Item [[dim]{transaction['item']}[/dim]]: ").strip()
    if new_item:
        transaction["item"] = new_item

    transaction["category"] = prompt_category(transaction["category"])

    new_amount = console.input(
        f"  Amount [[dim]${transaction['amount']:.2f}[/dim]]: "
    ).strip().lstrip("$")
    if new_amount:
        try:
            parsed = round(float(new_amount), 2)
            if parsed > 0:
                transaction["amount"] = parsed
            else:
                console.print("  [red]Amount must be greater than $0.00. Keeping original.[/red]")
        except ValueError:
            console.print("  [red]Invalid amount. Keeping original.[/red]")


def prompt_category(current: str) -> str:
    """Show a numbered category picker with search. Returns the selected category."""
    console.print(f"  [dim]Current: {current}[/dim]")

    def _show_grid():
        per_row = 3
        for i in range(0, len(CATEGORIES), per_row):
            chunk = CATEGORIES[i:i + per_row]
            parts = [f"[bold]{i + j + 1:>2}[/bold]) {cat:<25}" for j, cat in enumerate(chunk)]
            console.print("  " + " ".join(parts))

    _show_grid()

    while True:
        choice = console.input(
            "  Category # or name [[bold]Enter to keep[/bold]]: "
        ).strip()

        if choice == "":
            return current

        # Try number first
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(CATEGORIES):
                return CATEGORIES[idx]
        except ValueError:
            pass

        # Fuzzy text search
        query = choice.lower()
        matches = [c for c in CATEGORIES if query in c.lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            console.print(f"  [yellow]Multiple matches:[/yellow]")
            for m in matches:
                console.print(f"    {m}")
            continue

        console.print(f"  [red]No match. Enter 1-{len(CATEGORIES)}, search text, or Enter to keep[/red]")


def print_success(sheet_name: str, excel_path: str) -> None:
    console.print(f"  [bold green]Saved to \"{sheet_name}\" in {excel_path}[/bold green]")


def print_cancelled() -> None:
    console.print("  [dim]Skipped.[/dim]")


def print_error(message: str) -> None:
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")


def show_batch_table(transactions: list[dict], statuses: list[str]) -> None:
    """Render all transactions in a Rich table with status indicators."""
    table = Table(show_header=True, header_style="bold", pad_edge=False)
    table.add_column("#", justify="right", style="bold", width=3)
    table.add_column("Date", width=10)
    table.add_column("Item", min_width=15)
    table.add_column("Category", min_width=12)
    table.add_column("Amount", justify="right", width=10)
    table.add_column("", justify="center", width=2)

    for i, (txn, status) in enumerate(zip(transactions, statuses), 1):
        style = None
        indicator = ""
        if status == "skipped":
            style = "dim"
            indicator = "[dim]──[/dim]"
        elif status == "written":
            style = "dim"
            indicator = "[green]✓[/green]"
        elif status == "error":
            indicator = "[red]✗[/red]"

        table.add_row(
            str(i),
            txn["date"],
            txn["item"],
            txn["category"],
            f"${txn['amount']:.2f}",
            indicator,
            style=style,
        )

    console.print()
    console.print(table)


def _parse_numbers(text: str, count: int) -> list[int] | None:
    """Parse '1 2 3' or '1,2,3' or '1, 2, 3' into 0-based indices. Returns None on error."""
    # Split on commas and/or whitespace
    nums = [s.strip() for s in text.replace(",", " ").split()]
    indices = []
    for n in nums:
        try:
            idx = int(n) - 1
            if 0 <= idx < count:
                indices.append(idx)
            else:
                return None
        except ValueError:
            return None
    return indices if indices else None


def prompt_batch_action(count: int) -> tuple[str, list[int] | None]:
    """
    Prompt for batch-level action.

    Returns (action, indices) where action is one of:
    "all", "edit", "skip", "split", "quit"
    and indices is a list of 0-based indices (or None for "all"/"quit").
    Supports multiple numbers: "sk 7 8 9", "sk 7,8,9", "e 2, 5".
    """
    while True:
        raw = console.input(
            "\n  [bold]\\[a]ll write[/bold] / \\[e]dit # / \\[s]plit # / "
            "\\[sk]ip # / \\[q]uit [bold]\\[default: a][/bold]: "
        ).strip().lower()

        if raw in ("", "a", "all"):
            return ("all", None)

        if raw in ("q", "quit"):
            return ("quit", None)

        parts = raw.split(None, 1)
        cmd = parts[0]

        if cmd in ("e", "edit"):
            if len(parts) == 1 and count == 1:
                return ("edit", [0])
            if len(parts) == 2:
                indices = _parse_numbers(parts[1], count)
                if indices:
                    return ("edit", indices)
            console.print(f"  [red]Enter number(s) 1-{count}[/red]")
            continue

        if cmd in ("s", "split"):
            if len(parts) == 1 and count == 1:
                return ("split", [0])
            if len(parts) == 2:
                indices = _parse_numbers(parts[1], count)
                if indices:
                    return ("split", indices)
            console.print(f"  [red]Enter number(s) 1-{count}[/red]")
            continue

        if cmd in ("sk", "skip"):
            if len(parts) == 1 and count == 1:
                return ("skip", [0])
            if len(parts) == 2:
                indices = _parse_numbers(parts[1], count)
                if indices:
                    return ("skip", indices)
            console.print(f"  [red]Enter number(s) 1-{count}[/red]")
            continue

        console.print("  [red]Enter: a, e #, s #, sk #, or q[/red]")
