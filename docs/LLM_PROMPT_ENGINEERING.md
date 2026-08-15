# LLM Gateway & Prompt Engineering Specification

This document details the architecture of the **Resilient Dual-Provider LLM Gateway** (Google Gemini primary + Groq fallback) and prompt design for generating bilingual warnings.

---

## 1. Resilience Architecture (Gemini + Groq Failover)

```
                       ┌───────────────────────────────┐
                       │     Scored Risk & Metrics     │
                       └───────────────┬───────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │   Primary: Google Gemini API  │
                       │   (gemini-2.5-flash)          │
                       └───────────────┬───────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                   │ Success                               │ Failure (Timeout >10s / 429 / 5xx)
                   ▼                                       ▼
        ┌─────────────────────┐                 ┌─────────────────────┐
        │ Parse JSON Output   │                 │ Fallback: Groq API  │
        └─────────────────────┘                 │ (llama-3.3-70b)     │
                                                └──────────┬──────────┘
                                                           │
                                                           ▼
                                                ┌─────────────────────┐
                                                │ Parse JSON Output   │
                                                └─────────────────────┘
```

---

## 2. Structured System Prompt

The LLM is provided with a strict system instruction to return a validated JSON payload containing both English and Malayalam summaries:

```text
You are Malabar Watch, an AI early warning system for extreme rainfall and landslide risks in Kerala, India.
Your role is to summarize risk metrics into empathetic, clear, actionable advisories in BOTH English and Malayalam.

CRITICAL INSTRUCTIONS:
1. Return ONLY valid, minified JSON matching the exact schema below. Do not wrap in markdown code blocks.
2. Tone: Calm, authoritative, cautionary, empathetic.
3. NEVER contradict the provided Risk Level (e.g. if Risk Level is ORANGE / HIGH, do not say "Everything is fine").
4. In Malayalam, use proper disaster alert terminology (e.g. 'ഓറഞ്ച് അലർട്ട്', 'മണ്ണിടിച്ചിൽ സാധ്യത', 'ജാഗ്രതാ നിർദ്ദേശം').

JSON Output Schema:
{
  "summary_en": "2-sentence clear overview of current rainfall and risk state in English",
  "summary_ml": "2-sentence clear overview of current rainfall and risk state in Malayalam",
  "advisory_en": "Specific safety action items for residents in English",
  "advisory_ml": "Specific safety action items for residents in Malayalam"
}
```

---

## 3. User Prompt Payload Construction

```json
{
  "district": "Wayanad",
  "micro_zone": "Vythiri / Chooralmala belt",
  "assessed_risk_level": "ORANGE (HIGH)",
  "metrics": {
    "1h_mm": 18.2,
    "24h_mm": 142.5,
    "48h_mm": 218.0,
    "72h_mm": 265.4,
    "api_soil_saturation": "HIGH"
  },
  "historical_precedent": {
    "event": "2024 Wayanad Landslides",
    "relevance": "High 48h cumulative rainfall matching saturated pre-landslide conditions."
  }
}
```

---

## 4. Fallback Provider Implementation Specs

### Primary: Google Gemini (`src/llm/gemini.py`)
- **API Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`
- **Authentication:** `GEMINI_API_KEY`
- **Config:** `response_mime_type: "application/json"`, `temperature: 0.2`

### Fallback: Groq (`src/llm/groq.py`)
- **API Endpoint:** `https://api.groq.com/openai/v1/chat/completions`
- **Authentication:** `GROQ_API_KEY`
- **Model:** `llama-3.3-70b-versatile`
- **Config:** `response_format: {"type": "json_object"}`, `temperature: 0.2`
