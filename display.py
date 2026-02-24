from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def show_preview(transaction: dict) -> None:
    """Print a formatted table showing the parsed transaction."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Date", style="dim")
    table.add_column("Category")
    table.add_column("Item")
    table.add_column("Amount", justify="right", style="green")

    table.add_row(
        transaction["date"],
        transaction["category"],
        transaction["item"],
        f"${transaction['amount']:.2f}",
    )

    console.print()
    console.print(table)
    console.print()


def ask_corrections(transaction: dict) -> bool:
    """
    Prompt the user to correct item or category. Modifies transaction in place.
    Returns True if any changes were made.
    """
    response = console.input("[bold]Edit any fields?[/bold] [y/[bold]N[/bold]]: ").strip().lower()
    if response not in ("y", "yes"):
        return False

    changed = False

    new_item = console.input(f"Item [[dim]{transaction['item']}[/dim]]: ").strip()
    if new_item:
        transaction["item"] = new_item
        changed = True

    new_cat = console.input(f"Category [[dim]{transaction['category']}[/dim]]: ").strip()
    if new_cat:
        transaction["category"] = new_cat
        changed = True

    return changed


def ask_confirm() -> bool:
    """Prompt the user to confirm writing to Excel. Default is No."""
    response = console.input("[bold]Write this to Excel?[/bold] [y/[bold]N[/bold]]: ").strip().lower()
    return response in ("y", "yes")


def print_success(sheet_name: str, excel_path: str) -> None:
    console.print(f"\n[bold green]Row appended to sheet \"{sheet_name}\" in {excel_path}[/bold green]\n")


def print_cancelled() -> None:
    console.print("\n[dim]Cancelled. Nothing was written.[/dim]\n")


def print_error(message: str) -> None:
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


def print_info(message: str) -> None:
    console.print(f"[dim]{message}[/dim]")
