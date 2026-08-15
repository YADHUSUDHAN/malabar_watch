# Technical Architecture Blueprint - Malabar Watch

## 1. Overview & System Purpose
**Malabar Watch** is a self-hosted early-warning AI agent engineered specifically for high-risk monsoon districts in Kerala (Wayanad, Idukki, Kottayam). The system functions as an autonomous pipeline:

`Open-Meteo API (Ingestion)` ➔ `SQLite (Storage)` ➔ `Scoring Engine (Rule-based)` ➔ `Dual LLM Gateway (Gemini/Groq)` ➔ `Telegram Bot (Bilingual Push & On-Demand)`

---

## 2. Component Design & Responsibilities

### 2.1 Ingestion Engine (`src/ingestion/`)
- Runs hourly via `systemd timer` or Python scheduler.
- Fetches hourly precipitation data from Open-Meteo for defined district coordinates.
- Calculates rolling metrics: 1h, 24h, 48h, 72h totals, and the Antecedent Precipitation Index (API).
- Stores raw payloads and parsed values in SQLite.

### 2.2 Risk Scoring Engine (`src/risk_engine/`)
- Purely deterministic Python module (`scorer.py`).
- Loads configured threshold rules from `thresholds.yaml`.
- Evaluates risk levels: `LOW`, `MODERATE`, `HIGH`, `SEVERE`.
- Avoids delegating threshold math to the LLM to eliminate hallucination risk.

### 2.3 Historical Context Store (`src/data/historical_events.json`)
- Static JSON database containing landmark disaster metrics (e.g. Wayanad 2024, Pettimudi 2020, Kanjirappally 2021).
- Used by the LLM layer to ground generated warnings in real regional historical context.

### 2.4 Resilient LLM Layer (`src/llm/`)
- Abstract `LLMProvider` base class with concrete implementations:
  - `GeminiProvider` (Primary: `gemini-2.5-flash` or `gemini-1.5-flash`)
  - `GroqProvider` (Fallback: `llama-3.3-70b-versatile`)
- Automatically falls back to Groq if Gemini returns an error (429 rate limit, 503 unavailable, or connection timeout >10s).
- Prompts the LLM to output a strict JSON payload containing English and Malayalam advisories.

### 2.5 Telegram Bot Engine (`src/bot/`)
- Async Python Telegram bot using long polling.
- Zero inbound network ports open on the host machine.
- Manages user subscriptions stored in SQLite.
- Dispatches bilingual warnings on risk elevation or on demand via commands.

---

## 3. Database Schema (`src/db/schema.sql`)

```sql
-- Rainfall logs per district
CREATE TABLE IF NOT EXISTS rainfall_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id TEXT NOT NULL,
    recorded_at DATETIME NOT NULL,
    rainfall_1h REAL NOT NULL,
    rainfall_24h REAL NOT NULL,
    rainfall_48h REAL NOT NULL,
    rainfall_72h REAL NOT NULL,
    api_index REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Computed risk assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id TEXT NOT NULL,
    assessed_at DATETIME NOT NULL,
    risk_level TEXT NOT NULL, -- LOW, MODERATE, HIGH, SEVERE
    llm_provider_used TEXT NOT NULL, -- gemini / groq
    summary_en TEXT NOT NULL,
    summary_ml TEXT NOT NULL,
    advisory_en TEXT NOT NULL,
    advisory_ml TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Telegram subscribers
CREATE TABLE IF NOT EXISTS subscribers (
    chat_id INTEGER PRIMARY KEY,
    district_id TEXT NOT NULL DEFAULT 'all',
    subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

-- Alert delivery audit trail
CREATE TABLE IF NOT EXISTS alert_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_assessment_id INTEGER REFERENCES risk_assessments(id),
    district_id TEXT NOT NULL,
    dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    delivered_count INTEGER DEFAULT 0
);
```

---

## 4. End-to-End Control Flow

1. **Scheduled Trigger (Hourly):** Ingestion engine executes `fetch_rainfall.py`.
2. **API Fetch:** Calls Open-Meteo API for Wayanad, Idukki, Kottayam.
3. **Database Store:** Saves hourly data and updates rolling 24h, 48h, 72h totals in SQLite.
4. **Scoring Evaluation:** Passes cumulative stats to `scorer.py` ➔ evaluates current risk state.
5. **State Transition Check:** Compares new risk level against previous assessment.
6. **LLM Synthesis:** If risk state $\ge$ `MODERATE` or state escalated, requests bilingual summary from Gemini (or Groq on failover).
7. **Telegram Broadcast:** Dispatches bilingual message to all active subscribers for the district.
8. **On-Demand Requests:** User sends `/status wayanad` on Telegram ➔ Bot fetches latest risk state and returns formatted message immediately.
