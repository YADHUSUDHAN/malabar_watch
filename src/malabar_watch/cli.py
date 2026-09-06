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
    console.print(
        "\n[bold cyan]Evaluating Deterministic Landslide Risk (SPEC-002)...[/bold cyan]"
    )
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
    # Also support positional argument
    parser.add_argument(
        "command",
        nargs="?",
        choices=["test-ingest", "test-risk", "test-llm"],
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

    # Default quick demonstration assessment
    sample = evaluate_risk("Wayanad", 165.0, 110.0)
    console.print(
        f"[yellow]Sample Assessment:[/yellow] {sample.district} -> "
        f"Risk Level: [bold red]{sample.risk_level.value}[/bold red]"
    )
    console.print("\n[dim]Run 'malabar-watch --test-ingest' to test live Open-Meteo polling.[/dim]")
    console.print("[dim]Run 'malabar-watch --test-risk' to test deterministic risk engine.[/dim]")
    console.print(
        "[dim]Run 'malabar-watch --test-llm' to test bilingual LLM advisory synthesis.[/dim]"
    )
    return 0




if __name__ == "__main__":
    sys.exit(main())

