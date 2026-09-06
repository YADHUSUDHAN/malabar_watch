"""Unified Command Line Interface for Malabar Watch."""

import argparse
import asyncio
import sys

from rich.console import Console
from rich.table import Table

from malabar_watch import __version__
from malabar_watch.config import settings
from malabar_watch.ingestion import DEFAULT_TARGETS, DataIngestionService
from malabar_watch.risk_engine import evaluate_risk

# Ensure stdout/stderr handles UTF-8 on Windows consoles without charmap errors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()


async def run_test_ingestion() -> None:
    """Fetches live weather metrics from Open-Meteo and displays a summary table."""
    console.print(
        "\n[bold cyan]Querying Open-Meteo Weather API for Kerala Micro-Zones...[/bold cyan]"
    )
    service = DataIngestionService()

    try:
        metrics_dict = await service.fetch_and_process_all()

        table = Table(title="Live Weather Ingestion & Risk Metrics", border_style="cyan")
        table.add_column("District", style="bold")
        table.add_column("Micro-Zone", style="dim")
        table.add_column("Observed At")
        table.add_column("1h (mm)", justify="right")
        table.add_column("24h (mm)", justify="right")
        table.add_column("48h (mm)", justify="right")
        table.add_column("72h (mm)", justify="right")
        table.add_column("API Index", justify="right")

        for district_id, metrics in metrics_dict.items():
            target = DEFAULT_TARGETS.get(district_id)
            micro_zone = target.micro_zone if target else district_id
            table.add_row(
                district_id.title(),
                micro_zone,
                metrics.timestamp.strftime("%Y-%m-%d %H:%M"),
                f"{metrics.rainfall_1h:.1f}",
                f"{metrics.rainfall_24h:.1f}",
                f"{metrics.rainfall_48h:.1f}",
                f"{metrics.rainfall_72h:.1f}",
                f"{metrics.antecedent_index:.1f}",
            )

        console.print(table)
        console.print(
            "[bold green]✓ Ingestion complete. Observations persisted to SQLite "
            f"({settings.DATABASE_URL})[/bold green]\n"
        )
    except Exception as e:
        console.print(f"[bold red]Error during weather ingestion:[/bold red] {e}")
        raise


def main() -> int:
    """CLI Entry point for Malabar Watch agent."""
    parser = argparse.ArgumentParser(
        description="Malabar Watch - AI Rainfall & Landslide Early Warning Agent"
    )
    parser.add_argument(
        "--test-ingest",
        action="store_true",
        help="Poll live Open-Meteo weather data for Kerala districts and display metrics",
    )
    # Also support positional argument "test-ingest"
    parser.add_argument(
        "command",
        nargs="?",
        choices=["test-ingest"],
        help="Optional sub-command to execute",
    )

    args = parser.parse_args()

    console.print(f"[bold cyan]Malabar Watch (മലബാർ വാച്ച്)[/bold cyan] v{__version__}")
    console.print(f"[green]Environment:[/green] {settings.ENVIRONMENT}")
    console.print(f"[green]Database:[/green] {settings.DATABASE_URL}")

    if args.test_ingest or args.command == "test-ingest":
        asyncio.run(run_test_ingestion())
        return 0

    # Default quick demonstration assessment
    sample = evaluate_risk("Wayanad", 165.0, 110.0)
    console.print(
        f"[yellow]Sample Assessment:[/yellow] {sample.district} -> "
        f"Risk Level: [bold red]{sample.risk_level.value}[/bold red]"
    )
    console.print("\n[dim]Run 'malabar-watch --test-ingest' to test live Open-Meteo polling.[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
