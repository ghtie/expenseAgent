from display import console


def prompt_split(full_amount: float) -> float:
    """
    Interactively ask the user how to split the expense.
    Returns the final amount to record.
    """
    half = round(full_amount / 2, 2)

    console.print(f"[bold]Original amount:[/bold] ${full_amount:.2f}\n")
    console.print("How would you like to split this expense?")
    console.print(f"  [1] No split — record full amount (${full_amount:.2f})")
    console.print(f"  [2] 50/50 split — record half (${half:.2f})")
    console.print( "  [3] Custom split\n")

    while True:
        choice = console.input("Enter choice (1/2/3) [[bold]default: 1[/bold]]: ").strip()

        if choice in ("", "1"):
            return full_amount

        if choice == "2":
            console.print(f"\n[dim]Amount to record: ${half:.2f}[/dim]\n")
            return half

        if choice == "3":
            return _prompt_custom_split(full_amount)

        console.print("[red]Please enter 1, 2, or 3.[/red]")


def _prompt_custom_split(full_amount: float) -> float:
    """Prompt the user for a custom split amount or percentage."""
    console.print("\nEnter your custom split:")
    console.print("  Enter a dollar amount (e.g. 8.50) or a percentage (e.g. 60%)\n")

    while True:
        raw = console.input("Split: ").strip()
        try:
            result = _parse_custom_split(raw, full_amount)
            console.print(f"\n[dim]Amount to record: ${result:.2f}[/dim]\n")
            return result
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")


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
        raise ValueError("Please enter a dollar amount (e.g. 8.50) or a percentage (e.g. 60%).")

    if input_str.endswith("%"):
        try:
            pct = float(input_str[:-1])
        except ValueError:
            raise ValueError(f"Invalid percentage: '{input_str}'. Example: 60%")
        if not (0 < pct <= 100):
            raise ValueError("Percentage must be between 0 and 100.")
        result = round(full_amount * (pct / 100), 2)
    else:
        try:
            result = round(float(input_str), 2)
        except ValueError:
            raise ValueError(f"Invalid amount: '{input_str}'. Example: 8.50")

    if result <= 0:
        raise ValueError("Split amount must be greater than $0.00.")
    if result > full_amount:
        raise ValueError(f"Split amount ${result:.2f} exceeds the full amount ${full_amount:.2f}.")

    return result
