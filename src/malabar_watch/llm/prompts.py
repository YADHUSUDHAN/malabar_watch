"""System prompts, prompt payload builder, and JSON sanitization utilities."""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from malabar_watch.risk_engine.models import RiskAssessment

SYSTEM_PROMPT = """You are Malabar Watch, an early warning AI for extreme weather in Kerala.
Summarize deterministic risk metrics into empathetic, clear advisories in English and Malayalam.


CRITICAL SAFETY INSTRUCTIONS:
1. Return ONLY valid JSON matching this exact schema:
{
  "summary_en": "2-sentence clear overview of current rainfall and risk in English",
  "summary_ml": "2-sentence clear overview of current rainfall and risk in Malayalam",
  "advisory_en": "Actionable safety guidance for residents in English",
  "advisory_ml": "Actionable safety guidance for residents in Malayalam"
}
2. Do NOT include markdown code fences (like ```json), explanations, or surrounding text.
3. Tone: Calm, authoritative, cautionary, empathetic.
4. NEVER contradict the provided Risk Level (e.g. if HIGH, do not state "Everything is safe").
5. In Malayalam, use authentic regional disaster alert terminology:
   - Levels: 'ഹരിതം' (Low), 'മഞ്ഞ ജാഗ്രത' (Moderate), 'ഓറഞ്ച് അലർട്ട്' (High), 'റെഡ് അലർട്ട്' (Severe)
   - Hazards: 'മണ്ണിടിച്ചിൽ സാധ്യത', 'ഉരുൾപൊട്ടൽ സാധ്യത', 'മലവെള്ളപ്പാച്ചിൽ'
   - Directives: 'നദിക്കരയിലുള്ളവർ ജാഗ്രത പാലിക്കുക', 'സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക'
6. If a historical precedent is provided, reference it succinctly to ground warning urgency.
"""



def build_advisory_prompt(assessment: "RiskAssessment") -> str:
    """Builds a structured prompt from a deterministic RiskAssessment."""
    precedent_text = "None recorded for this condition."
    if assessment.historical_event:
        precedent_text = (
            f"{assessment.historical_event.location} ({assessment.historical_event.date}) - "
            f"Peak 24h: {assessment.historical_event.rainfall_24h_mm:.1f}mm. "
            f"Trigger: {assessment.historical_event.key_trigger}. "
            f"Impact: {assessment.historical_event.consequence}."
        )

    rules_text = (
        "\n".join(f"- {r}" for r in assessment.triggered_rules)
        if assessment.triggered_rules
        else "- Normal baseline readings"
    )

    return f"""Target District / Micro-Zone: {assessment.district.title()}
Deterministic Risk Level: {assessment.risk_level.value} ({assessment.risk_level.badge})
State Transition: {assessment.escalation_state.value}

Precipitation Metrics:
- Trailing 1h Rainfall: {assessment.rainfall_1h:.1f} mm
- Trailing 24h Cumulative: {assessment.rainfall_24h:.1f} mm
- Trailing 48h Cumulative: {assessment.rainfall_48h:.1f} mm
- Trailing 72h Cumulative: {assessment.rainfall_72h:.1f} mm
- Antecedent Precipitation Index (Soil Saturation API): {assessment.antecedent_index:.1f}

Triggered Geotechnical Threshold Rules:
{rules_text}

Historical Regional Disaster Precedent:
{precedent_text}

Generate the structured JSON advisory for the residents and emergency responders."""


def sanitize_json_output(raw_text: str) -> str:
    """Strips markdown code blocks, whitespace, and isolates JSON object payload."""
    cleaned = raw_text.strip()

    # Strip markdown ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    # Extract bracketed JSON substring if extraneous content surrounds it
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]

    return cleaned
