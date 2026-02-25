from rich.console import Console

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
    """Prompt for item and category edits. Modifies transaction in place."""
    new_item = console.input(f"  Item [[dim]{transaction['item']}[/dim]]: ").strip()
    if new_item:
        transaction["item"] = new_item

    transaction["category"] = prompt_category(transaction["category"])


def prompt_category(current: str) -> str:
    """Show a numbered category picker. Returns the selected category."""
    console.print(f"  [dim]Current: {current}[/dim]")

    per_row = 3
    for i in range(0, len(CATEGORIES), per_row):
        chunk = CATEGORIES[i:i + per_row]
        parts = [f"[bold]{i + j + 1:>2}[/bold]) {cat:<25}" for j, cat in enumerate(chunk)]
        console.print("  " + " ".join(parts))

    while True:
        choice = console.input(
            "  Category # [[bold]Enter to keep[/bold]]: "
        ).strip()

        if choice == "":
            return current

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(CATEGORIES):
                return CATEGORIES[idx]
        except ValueError:
            pass

        console.print(f"  [red]Enter 1-{len(CATEGORIES)} or press Enter to keep[/red]")


def print_success(sheet_name: str, excel_path: str) -> None:
    console.print(f"  [bold green]Saved to \"{sheet_name}\" in {excel_path}[/bold green]")


def print_cancelled() -> None:
    console.print("  [dim]Skipped.[/dim]")


def print_error(message: str) -> None:
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")
