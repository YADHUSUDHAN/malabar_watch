"""Unified Command Line Interface for Malabar Watch."""

import sys

from rich.console import Console

from malabar_watch import __version__
from malabar_watch.config import settings
from malabar_watch.risk_engine import evaluate_risk

console = Console()


def main() -> None:
    """CLI Entry point for Malabar Watch agent."""
    console.print(f"[bold cyan]Malabar Watch (മലബാർ വാച്ച്)[/bold cyan] v{__version__}")
    console.print(f"[green]Environment:[/green] {settings.ENVIRONMENT}")
    console.print(f"[green]Database:[/green] {settings.DATABASE_URL}")

    # Run quick demonstration assessment
    sample = evaluate_risk("Wayanad", 165.0, 110.0)
    console.print(
        f"[yellow]Sample Assessment:[/yellow] {sample.district} -> "
        f"Risk Level: [bold red]{sample.risk_level.value}[/bold red]"
    )


if __name__ == "__main__":
    sys.exit(main())
