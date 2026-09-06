"""Unified Command Line Interface for Malabar Watch."""

import argparse
import asyncio
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from malabar_watch import __version__
from malabar_watch.config import settings
from malabar_watch.ingestion import DEFAULT_TARGETS, DataIngestionService
from malabar_watch.ingestion.models import PrecipitationMetrics
from malabar_watch.llm import DualLLMGateway
from malabar_watch.risk_engine import (
    RiskAssessmentService,
    RiskLevel,
    evaluate_risk,
)

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


async def run_test_risk() -> None:
    """Evaluates deterministic landslide risk and historical precedent for all micro-zones."""
    console.print("\n[bold cyan]Evaluating Deterministic Landslide Risk (SPEC-002)...[/bold cyan]")
    ingest_service = DataIngestionService()
    risk_service = RiskAssessmentService()

    try:
        metrics_dict = await ingest_service.fetch_and_process_all()
    except Exception as e:
        console.print(
            "[yellow]Notice: Live fetch failed ("
            f"{e}). Evaluating synthetic verification dataset.[/yellow]"
        )
        now = datetime.now()
        metrics_dict = {
            "wayanad": PrecipitationMetrics(
                district_id="wayanad",
                timestamp=now,
                rainfall_1h=28.0,
                rainfall_24h=210.0,
                rainfall_48h=360.0,
                rainfall_72h=410.0,
                antecedent_index=162.0,
            ),
            "idukki": PrecipitationMetrics(
                district_id="idukki",
                timestamp=now,
                rainfall_1h=12.0,
                rainfall_24h=145.0,
                rainfall_48h=190.0,
                rainfall_72h=220.0,
                antecedent_index=125.0,
            ),
            "kottayam": PrecipitationMetrics(
                district_id="kottayam",
                timestamp=now,
                rainfall_1h=5.0,
                rainfall_24h=65.0,
                rainfall_48h=98.0,
                rainfall_72h=115.0,
                antecedent_index=72.0,
            ),
        }

    assessments = risk_service.assess_all(metrics_dict)

    table = Table(
        title="Malabar Watch - Deterministic Risk Assessment (SPEC-002)",
        border_style="magenta",
        show_lines=True,
    )
    table.add_column("District / Micro-Zone", style="bold")
    table.add_column("Risk Level", justify="center")
    table.add_column("Transition State", justify="center")
    table.add_column("Alert Required?", justify="center")
    table.add_column("24h / 48h / API", justify="right")
    table.add_column("Historical Precedent", style="cyan")
    table.add_column("Triggered Audit Rules", style="dim")

    level_styles = {
        RiskLevel.LOW: "[green]🟢 LOW[/green]",
        RiskLevel.MODERATE: "[yellow]🟡 MODERATE[/yellow]",
        RiskLevel.HIGH: "[bold dark_orange]🟠 HIGH[/bold dark_orange]",
        RiskLevel.SEVERE: "[bold red]🔴 SEVERE[/bold red]",
    }

    for district_id, assessment in assessments.items():
        target = DEFAULT_TARGETS.get(district_id)
        zone_label = f"{district_id.title()}\n[dim]({target.micro_zone if target else ''})[/dim]"

        lvl_badge = level_styles.get(assessment.risk_level, assessment.risk_level.value)

        alert_badge = (
            "[bold red]YES (Dispatch)[/bold red]"
            if assessment.requires_alert
            else "[dim green]NO (Suppressed)[/dim green]"
        )

        metrics_summary = (
            f"24h: {assessment.rainfall_24h:.1f}mm\n"
            f"48h: {assessment.rainfall_48h:.1f}mm\n"
            f"API: {assessment.antecedent_index:.1f}"
        )

        hist_summary = (
            f"[bold]{assessment.historical_event.event_id}[/bold]\n"
            f"{assessment.historical_event.location} ({assessment.historical_event.date})"
            if assessment.historical_event
            else "[dim]None[/dim]"
        )

        if assessment.triggered_rules:
            rules_summary = "\n".join(f"• {r}" for r in assessment.triggered_rules)
        else:
            rules_summary = "[dim]Normal Baseline[/dim]"

        table.add_row(
            zone_label,
            lvl_badge,
            assessment.escalation_state.value,
            alert_badge,
            metrics_summary,
            hist_summary,
            rules_summary,
        )

    console.print(table)
    console.print(
        "[bold green]✓ Risk scoring complete. Assessments saved to database "
        f"({settings.DATABASE_URL})[/bold green]\n"
    )


async def run_test_llm() -> None:
    """Tests bilingual advisory synthesis via Gemini/Groq failover gateway."""
    console.print(
        "\n[bold cyan]Synthesizing Bilingual Advisory via Dual-LLM Gateway "
        "(SPEC-003)...[/bold cyan]"
    )

    # Use an elevated simulated scenario (Wayanad SEVERE event) to verify full prompt & grounding
    assessment = evaluate_risk(
        district="wayanad",
        rainfall_24h=215.0,
        api_index=158.0,
        rainfall_48h=365.0,
        rainfall_1h=28.0,
    )

    gateway = DualLLMGateway()
    advisory = await gateway.generate_advisory(assessment)

    provider_colors = {
        "gemini": "[bold blue]Google Gemini (Primary)[/bold blue]",
        "groq": "[bold green]Groq Cloud (Fallback)[/bold green]",
        "template": (
            "[bold yellow]Deterministic Rule-Based Template (Offline Fallback)[/bold yellow]"
        ),
    }
    provider_label = provider_colors.get(advisory.provider_used, advisory.provider_used)

    target_obj = DEFAULT_TARGETS.get("wayanad", None)
    micro_zone_label = target_obj.micro_zone if target_obj else ""

    panel_content = (
        f"[bold]Target Micro-Zone:[/bold] {advisory.district_id.title()} "
        f"([dim]{micro_zone_label}[/dim])\n"
        f"[bold]Risk Level:[/bold] {advisory.risk_level.badge}\n"
        f"[bold]LLM Provider Used:[/bold] {provider_label}  |  "
        f"[bold]Latency:[/bold] {advisory.latency_ms}ms\n\n"
        f"[bold cyan]── English Advisory (ഇംഗ്ലീഷ്) ──[/bold cyan]\n"
        f"[bold]Summary:[/bold] {advisory.summary_en}\n"
        f"[bold]Action Guidance:[/bold] {advisory.advisory_en}\n\n"
        f"[bold yellow]── Malayalam Advisory (മലയാളം) ──[/bold yellow]\n"
        f"[bold]സംഗ്രഹം:[/bold] {advisory.summary_ml}\n"
        f"[bold]നിർദ്ദേശം:[/bold] {advisory.advisory_ml}"
    )

    console.print(
        Panel(
            panel_content,
            title="[bold magenta]Malabar Watch - Bilingual Early Warning Advisory[/bold magenta]",
            border_style="cyan",
        )
    )
    console.print(
        "[bold green]✓ LLM synthesis complete. Grounded, verified bilingual payload ready "
        "for broadcast.[/bold green]\n"
    )


async def run_test_bot() -> None:
    """Simulates Telegram bot HTML formatting and alert broadcast dispatch."""
    from malabar_watch.bot import AlertDispatcher, format_alert_html
    from malabar_watch.storage import DatabaseManager

    console.print(
        "\n[bold cyan]Simulating Telegram Bot Dispatch & Formatting (SPEC-004)...[/bold cyan]"
    )
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db = DatabaseManager(db_path=db_path)
    db.initialize_schema()

    # Register demo subscribers for simulation
    db.add_subscriber(chat_id=1001, district_id="wayanad")
    db.add_subscriber(chat_id=1002, district_id="idukki")
    db.add_subscriber(chat_id=9999, district_id="all")

    # Sample assessment
    now = datetime.now()
    metrics = PrecipitationMetrics(
        district_id="wayanad",
        rainfall_1h=32.0,
        rainfall_24h=218.0,
        rainfall_48h=312.0,
        rainfall_72h=360.0,
        antecedent_index=162.0,
        timestamp=now,
    )
    risk_service = RiskAssessmentService(db_manager=db)
    assessment = risk_service.assess_metrics(metrics)

    gateway = DualLLMGateway()
    advisory = await gateway.generate_advisory(assessment)

    # Format HTML
    html_msg = format_alert_html(assessment, advisory)

    console.print(
        Panel(
            html_msg,
            title="[bold blue]Simulated Telegram HTML Payload (SPEC-004)[/bold blue]",
            border_style="green",
        )
    )

    dispatcher = AlertDispatcher(db=db)
    stats = await dispatcher.dispatch_alert(
        assessment=assessment,
        advisory=advisory,
        dry_run=True,
    )

    deliv = stats["delivered"]
    fail = stats["failed"]
    tot = stats["total"]
    console.print(
        f"[bold green]✓ Simulated Dispatch Complete:[/bold green] "
        f"Delivered: {deliv} | Failed: {fail} | Total Target Subs: {tot}\n"
    )


def run_bot() -> None:
    """Runs the live Telegram bot using outbound long polling."""
    from malabar_watch.bot import TelegramBotService

    if not settings.TELEGRAM_BOT_TOKEN:
        console.print(
            "[bold red]Error: TELEGRAM_BOT_TOKEN is not set.[/bold red]\n"
            "Please create a bot with @BotFather and set TELEGRAM_BOT_TOKEN in your .env file."
        )
        sys.exit(1)

    service = TelegramBotService()
    console.print(
        "[bold green]Starting Malabar Watch Telegram bot daemon (Long Polling)...[/bold green]"
    )
    service.run_polling()


async def run_pipeline(dry_run: bool = True) -> None:
    """Executes a complete single-pass cycle of the autonomous pipeline."""
    from malabar_watch.pipeline import PipelineRunner

    console.print(
        "\n[bold cyan]Executing Full Autonomous Pipeline Cycle (SPEC 001-004)...[/bold cyan]"
    )
    runner = PipelineRunner()
    results = await runner.run_cycle(dry_run=dry_run, force_alert=True)

    table = Table(title="Pipeline Execution Summary", border_style="cyan")
    table.add_column("District", style="bold")
    table.add_column("Risk Level")
    table.add_column("Escalation")
    table.add_column("Advisory Synthesized")
    table.add_column("Dispatched")

    for district_id, res in results.items():
        table.add_row(
            district_id.title(),
            res.get("risk_level", "N/A"),
            res.get("escalation_state", "N/A"),
            "✓" if "advisory" in res else "-",
            "✓" if res.get("dispatched") else "-",
        )

    console.print(table)
    console.print("[bold green]✓ Pipeline cycle completed successfully.[/bold green]\n")


def main() -> int:
    """CLI Entry point for Malabar Watch agent."""
    from malabar_watch.logging import setup_logging

    setup_logging()

    parser = argparse.ArgumentParser(
        description="Malabar Watch - AI Rainfall & Landslide Early Warning Agent"
    )
    parser.add_argument(
        "--test-ingest",
        action="store_true",
        help="Poll live Open-Meteo weather data for Kerala districts and display metrics",
    )
    parser.add_argument(
        "--test-risk",
        action="store_true",
        help="Run deterministic risk scoring and historical grounding across all micro-zones",
    )
    parser.add_argument(
        "--test-llm",
        action="store_true",
        help="Test resilient bilingual advisory generation via Gemini / Groq / Template gateway",
    )
    parser.add_argument(
        "--test-bot",
        action="store_true",
        help="Simulate Telegram HTML formatting and subscriber broadcast dispatch",
    )
    parser.add_argument(
        "--bot",
        action="store_true",
        help="Start the Telegram bot daemon in outbound long-polling mode (Zero Inbound Ports)",
    )
    parser.add_argument(
        "--run-pipeline",
        action="store_true",
        help="Execute a single full pipeline cycle (Ingest -> Risk -> LLM -> Telegram Dispatch)",
    )
    # Also support positional argument
    parser.add_argument(
        "command",
        nargs="?",
        choices=["test-ingest", "test-risk", "test-llm", "test-bot", "bot", "run-pipeline"],
        help="Optional sub-command to execute",
    )

    args = parser.parse_args()

    console.print(f"[bold cyan]Malabar Watch (മലബാർ വാച്ച്)[/bold cyan] v{__version__}")
    console.print(f"[green]Environment:[/green] {settings.ENVIRONMENT}")
    console.print(f"[green]Database:[/green] {settings.DATABASE_URL}")

    if args.test_ingest or args.command == "test-ingest":
        asyncio.run(run_test_ingestion())
        return 0

    if args.test_risk or args.command == "test-risk":
        asyncio.run(run_test_risk())
        return 0

    if args.test_llm or args.command == "test-llm":
        asyncio.run(run_test_llm())
        return 0

    if args.test_bot or args.command == "test-bot":
        asyncio.run(run_test_bot())
        return 0

    if args.bot or args.command == "bot":
        run_bot()
        return 0

    if args.run_pipeline or args.command == "run-pipeline":
        asyncio.run(run_pipeline(dry_run=True))
        return 0

    # Default quick demonstration assessment
    sample = evaluate_risk("Wayanad", 165.0, 110.0)
    console.print(
        f"[yellow]Sample Assessment:[/yellow] {sample.district} -> "
        f"Risk Level: [bold red]{sample.risk_level.value}[/bold red]"
    )
    console.print("\n[dim]Commands available:[/dim]")
    console.print("  [dim]• malabar-watch --test-ingest   (Test Open-Meteo polling)[/dim]")
    console.print("  [dim]• malabar-watch --test-risk     (Test deterministic risk engine)[/dim]")
    console.print("  [dim]• malabar-watch --test-llm      (Test bilingual LLM advisory)[/dim]")
    console.print("  [dim]• malabar-watch --test-bot      (Simulate Telegram alert)[/dim]")
    console.print("  [dim]• malabar-watch --run-pipeline  (Run full end-to-end cycle)[/dim]")
    console.print("  [dim]• malabar-watch --bot           (Start live Telegram bot daemon)[/dim]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
