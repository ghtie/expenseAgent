from expense_agent.display import console


def prompt_split(full_amount: float) -> float:
    """
    Compact split prompt. Returns the final amount to record.
    """
    half = round(full_amount / 2, 2)

    while True:
        choice = console.input(
            f"  [1] Full [green]${full_amount:.2f}[/green]  "
            f"[2] Half [green]${half:.2f}[/green]  "
            f"[3] Equal split  "
            f"[4] Custom "
            f"[[bold]default: 2[/bold]]: "
        ).strip()

        if choice == "1":
            return full_amount
        if choice in ("", "2"):
            return half
        if choice == "3":
            return _prompt_equal_split(full_amount)
        if choice == "4":
            return _prompt_custom_split(full_amount)

        console.print("  [red]Enter 1, 2, 3, or 4.[/red]")


def _prompt_equal_split(full_amount: float) -> float:
    """Prompt for number of people and return an equal share."""
    while True:
        raw = console.input("  Split among how many people? ").strip()
        try:
            n = int(raw)
            if n < 2:
                console.print("  [red]Must be at least 2 people.[/red]")
                continue
            share = round(full_amount / n, 2)
            console.print(f"  [green]${full_amount:.2f} ÷ {n} = ${share:.2f}[/green]")
            return share
        except ValueError:
            console.print("  [red]Enter a whole number (e.g. 3).[/red]")


def _prompt_custom_split(full_amount: float) -> float:
    """Prompt the user for a custom split amount or percentage."""
    while True:
        raw = console.input("  Amount or % (e.g. 8.50 or 60%): ").strip()
        try:
            return _parse_custom_split(raw, full_amount)
        except ValueError as exc:
            console.print(f"  [red]{exc}[/red]")


def _parse_custom_split(input_str: str, full_amount: float) -> float:
    """
    Parse a custom split input string.

    Accepts:
        "8.50"  — dollar amount
        "60%"   — percentage of the full amount

    Returns the computed split amount, rounded to 2 decimal places.
    Raises ValueError on invalid or out-of-range input.
    """
    input_str = input_str.strip()

    if not input_str:
        raise ValueError("Enter a dollar amount (e.g. 8.50) or percentage (e.g. 60%).")

    if input_str.endswith("%"):
        try:
            pct = float(input_str[:-1])
        except ValueError:
            raise ValueError(f"Invalid percentage: '{input_str}'. Example: 60%")
        if pct <= 0:
            raise ValueError("Percentage must be greater than 0.")
        result = round(full_amount * (pct / 100), 2)
    else:
        try:
            result = round(float(input_str), 2)
        except ValueError:
            raise ValueError(f"Invalid amount: '{input_str}'. Example: 8.50")

    if result <= 0:
        raise ValueError("Split amount must be greater than $0.00.")

    return result
