"""HTML formatting utilities for Telegram alerts and interactive status cards."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

from malabar_watch.ingestion import DEFAULT_TARGETS
from malabar_watch.risk_engine import RiskLevel

if TYPE_CHECKING:
    from malabar_watch.ingestion.models import PrecipitationMetrics
    from malabar_watch.llm.models import BilingualAdvisory
    from malabar_watch.risk_engine.models import RiskAssessment


RISK_BADGES = {
    RiskLevel.LOW: "🟢 <b>LOW RISK / ഹരിതം</b>",
    RiskLevel.MODERATE: "🟡 <b>MODERATE ALERT / മഞ്ഞ അലർട്ട്</b>",
    RiskLevel.HIGH: "🟠 <b>ORANGE ALERT / ഓറഞ്ച് അലർട്ട് (HIGH)</b>",
    RiskLevel.SEVERE: "🔴 <b>RED ALERT / ചുവപ്പ് അലർട്ട് (SEVERE)</b>",
}

DISCLAIMER_FOOTNOTE = (
    "⚠️ <i>Malabar Watch is an automated AI experimental project. "
    "In emergencies, strictly follow official IMD & KSDMA directives "
    "(Toll-Free: 1077 / 1070 | NDRF: 112).</i>"
)


def get_micro_zone_label(district_id: str) -> str:
    """Returns human-friendly district and micro-zone name."""
    norm = district_id.lower().strip()
    target = DEFAULT_TARGETS.get(norm)
    if target:
        return f"{target.name} ({target.micro_zone})"
    return norm.title()


def format_alert_html(assessment: RiskAssessment, advisory: BilingualAdvisory) -> str:
    """Formats an autonomous push alert into structured Telegram HTML.

    Args:
        assessment: Deterministic RiskAssessment record.
        advisory: Grounded BilingualAdvisory synthesized by DualLLMGateway.

    Returns:
        HTML formatted string for Telegram send_message.
    """
    badge = RISK_BADGES.get(assessment.risk_level, f"⚠️ <b>{assessment.risk_level.value}</b>")
    region_label = html.escape(get_micro_zone_label(assessment.district))
    assessed_str = assessment.assessed_at.strftime("%Y-%m-%d %H:%M")

    # Historical context block
    hist_block = ""
    if assessment.historical_event:
        ev = assessment.historical_event
        ev_title = html.escape(f"{ev.district.title()} - {ev.location}")
        ev_summary = html.escape(ev.consequence)
        hist_block = (
            f"\n📜 <b>ചരിത്രപരമായ പശ്ചാത്തലം / Historical Precedent:</b>\n"
            f"• <b>{ev_title} ({ev.date}):</b> <i>{ev_summary}</i>\n"
            f"───────────────────────────\n"
        )

    summary_en = html.escape(advisory.summary_en)
    advisory_en = html.escape(advisory.advisory_en)
    summary_ml = html.escape(advisory.summary_ml)
    advisory_ml = html.escape(advisory.advisory_ml)

    msg = (
        f"🚨 <b>MALABAR WATCH WARNING | മലബാർ വാച്ച് മുന്നറിയിപ്പ്</b>\n"
        f"───────────────────────────\n"
        f"📍 <b>മേഖല / Region:</b> {region_label}\n"
        f"⚠️ <b>അപകട സാധ്യത / Status:</b> {badge}\n"
        f"⏱️ <i>{assessed_str} IST</i>\n\n"
        f"🌧️ <b>മഴ കണക്കുകൾ / Rainfall Metrics:</b>\n"
        f" • 1 മണിക്കൂർ (1h): <b>{assessment.rainfall_1h:.1f} mm</b>\n"
        f" • 24 മണിക്കൂർ (24h): <b>{assessment.rainfall_24h:.1f} mm</b>\n"
        f" • 48 മണിക്കൂർ (48h): <b>{assessment.rainfall_48h:.1f} mm</b>\n"
        f" • മണ്ണിലെ ജലാംശം (API): <b>{assessment.antecedent_index:.1f}</b>\n"
        f"───────────────────────────\n"
        f"<b>English Advisory (ഇംഗ്ലീഷ്):</b>\n"
        f"{summary_en}\n"
        f"👉 <i>{advisory_en}</i>\n"
        f"───────────────────────────\n"
        f"<b>മലയാളം നിർദ്ദേശം:</b>\n"
        f"{summary_ml}\n"
        f"👉 <i>{advisory_ml}</i>\n"
        f"───────────────────────────\n"
        f"{hist_block}"
        f"{DISCLAIMER_FOOTNOTE}"
    )
    return msg


def format_status_html(
    metrics: PrecipitationMetrics,
    assessment: RiskAssessment,
    advisory: BilingualAdvisory | None = None,
) -> str:
    """Formats an on-demand status inquiry response into Telegram HTML."""
    badge = RISK_BADGES.get(assessment.risk_level, f"⚠️ <b>{assessment.risk_level.value}</b>")
    region_label = html.escape(get_micro_zone_label(metrics.district_id))
    observed_str = metrics.timestamp.strftime("%Y-%m-%d %H:%M")

    advisory_block = ""
    if advisory:
        summary_en = html.escape(advisory.summary_en)
        advisory_en = html.escape(advisory.advisory_en)
        summary_ml = html.escape(advisory.summary_ml)
        advisory_ml = html.escape(advisory.advisory_ml)
        advisory_block = (
            f"\n───────────────────────────\n"
            f"<b>English Advisory:</b>\n{summary_en}\n👉 <i>{advisory_en}</i>\n\n"
            f"<b>മലയാളം നിർദ്ദേശം:</b>\n{summary_ml}\n👉 <i>{advisory_ml}</i>\n"
        )

    msg = (
        f"📊 <b>MALABAR WATCH LIVE STATUS | തത്സമയ സ്ഥിതി</b>\n"
        f"───────────────────────────\n"
        f"📍 <b>മേഖല / Region:</b> {region_label}\n"
        f"⚠️ <b>അപകട സാധ്യത / Status:</b> {badge}\n"
        f"⏱️ <i>Observed: {observed_str} IST</i>\n\n"
        f"🌧️ <b>Cumulative Rainfall:</b>\n"
        f" • Trailing 1h: <b>{metrics.rainfall_1h:.1f} mm</b>\n"
        f" • Trailing 24h: <b>{metrics.rainfall_24h:.1f} mm</b>\n"
        f" • Trailing 48h: <b>{metrics.rainfall_48h:.1f} mm</b>\n"
        f" • Trailing 72h: <b>{metrics.rainfall_72h:.1f} mm</b>\n"
        f" • Soil Moisture Index (API): <b>{metrics.antecedent_index:.1f}</b>"
        f"{advisory_block}\n"
        f"───────────────────────────\n"
        f"{DISCLAIMER_FOOTNOTE}"
    )
    return msg


def format_history_html(district: str, records: list[dict[str, Any]]) -> str:
    """Formats 24h/48h/72h historical rainfall trend into a clean Telegram HTML view."""
    region_label = html.escape(get_micro_zone_label(district))

    if not records:
        return (
            f"📈 <b>Rainfall History: {region_label}</b>\n\n"
            "<i>No recent rainfall observations recorded yet in database. "
            "Please check back after the next scheduled hourly ingestion.</i>"
        )

    lines = [
        f"📈 <b>Rainfall Trend (കഴിഞ്ഞ മഴക്കണക്കുകൾ): {region_label}</b>",
        "───────────────────────────",
        "<code>Timestamp        | 1h   | 24h   | API</code>",
        "───────────────────────────",
    ]

    # Show up to 8 recent points
    for r in records[:8]:
        ts = str(r.get("timestamp", ""))[:16]
        r1h = float(r.get("precipitation_mm", 0.0))
        r24h = float(r.get("rainfall_24h", 0.0))
        api = float(r.get("antecedent_index", 0.0))
        lines.append(f"<code>{ts:<16} | {r1h:>4.1f} | {r24h:>5.1f} | {api:>5.1f}</code>")

    lines.append("───────────────────────────")
    lines.append("💡 <i>High API (>100) indicates dangerous soil moisture saturation.</i>\n")
    lines.append(DISCLAIMER_FOOTNOTE)
    return "\n".join(lines)


def format_welcome_html() -> str:
    """Formats /start greeting and interactive bot onboarding message."""
    return (
        "👋 <b>Welcome to Malabar Watch (മലബാർ വാച്ച്)</b>\n"
        "<i>AI-Powered Rainfall & Landslide Early-Warning Agent for Kerala.</i>\n"
        "───────────────────────────\n"
        "Malabar Watch continuously monitors high-resolution Open-Meteo weather "
        "data across vulnerable Western Ghats regions (Wayanad, Idukki, Kottayam), "
        "evaluates geotechnical landslide saturation thresholds, and provides "
        "bilingual early warnings in English & മലയാളം.\n\n"
        "<b>Available Commands:</b>\n"
        "• /status - Check live rainfall & risk level\n"
        "• /subscribe - Receive automated emergency alerts\n"
        "• /unsubscribe - Opt-out of alerts\n"
        "• /history - View trailing rainfall trend\n"
        "• /disclaimer - Educational safety scope & emergency contacts\n"
        "• /help - Detailed assistance\n\n"
        "👇 <b>Select a district below for immediate live status:</b>"
    )


def format_help_html() -> str:
    """Formats /help command instructions and official emergency hotlines."""
    return (
        "ℹ️ <b>Malabar Watch Bot Help & Helplines | സഹായം</b>\n"
        "───────────────────────────\n"
        "<b>Bot Commands / കമാൻഡുകൾ:</b>\n"
        "• <code>/status [district]</code> - Live rainfall, soil moisture & risk\n"
        "• <code>/subscribe [district]</code> - Register for emergency push alerts\n"
        "• <code>/unsubscribe</code> - Stop automated alerts\n"
        "• <code>/history [district]</code> - View trailing 24h rainfall trends\n"
        "• <code>/disclaimer</code> - Safety disclaimer and project terms\n\n"
        "🚨 <b>Kerala Emergency Helplines (അടിയന്തര നമ്പറുകൾ):</b>\n"
        "• <b>National Emergency / Police:</b> <code>112</code> / <code>100</code>\n"
        "• <b>State Disaster Control Room (KSDMA):</b> <code>1070</code> (Toll-free)\n"
        "• <b>District Disaster Management (DEOC):</b> <code>1077</code> (Toll-free)\n"
        "• <b>Fire & Rescue Services (അഗ്നിശമന സേന):</b> <code>101</code>\n"
        "• <b>Ambulance / Medical (ആംബുലൻസ്):</b> <code>108</code>\n\n"
        "📍 <b>District Control Rooms (കലക്ടറേറ്റ് കൺട്രോൾ റൂം):</b>\n"
        "• <b>Wayanad DEOC:</b> <code>04936-204151</code> | Mob: <code>9562804151</code>\n"
        "• <b>Idukki DEOC:</b> <code>04862-233111</code> | Mob: <code>9383463036</code>\n"
        "• <b>Kottayam DEOC:</b> <code>0481-2562201</code>\n\n"
        "⚡ <b>Utilities Emergency:</b>\n"
        "• <b>KSEB Electricity:</b> <code>1912</code>\n"
        "• <b>Water Authority (KWA):</b> <code>1916</code>\n"
        "───────────────────────────\n"
        "<i>In extreme emergencies, strictly follow directives from Revenue, Police, and NDRF.</i>"
    )


def format_disclaimer_html() -> str:
    """Formats /disclaimer project scope and emergency hotlines."""
    return (
        "⚠️ <b>OFFICIAL DISCLAIMER & EMERGENCY CONTACTS</b>\n"
        "───────────────────────────\n"
        "<b>Educational & Portfolio Project Notice:</b>\n"
        "Malabar Watch is an independent, automated engineering and AI agent "
        "project. It is <b>NOT</b> an official government service and must NOT "
        "be considered a replacement for the India Meteorological Department (IMD) "
        "or the Kerala State Disaster Management Authority (KSDMA).\n\n"
        "🚨 <b>Emergency Helpline Numbers (Kerala):</b>\n"
        "• <b>KSDMA State Emergency Operations:</b> 1070 (Toll-free)\n"
        "• <b>District Emergency Operations:</b> 1077 (Toll-free)\n"
        "• <b>National Emergency Number / Police / Fire:</b> 112\n"
        "• <b>Wayanad District Control Room:</b> 04936-204151\n"
        "• <b>Idukki District Control Room:</b> 04862-233111\n"
        "• <b>Kottayam District Control Room:</b> 0481-2562201\n"
        "───────────────────────────\n"
        "<i>Always evacuate when directed by local revenue, police, "
        "and disaster management authorities.</i>"
    )
