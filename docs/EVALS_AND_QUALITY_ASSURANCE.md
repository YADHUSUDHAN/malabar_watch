# Standard Practices, LLM Evals & Quality Assurance Blueprint

This document outlines the **Standard Software Engineering Practices**, **LLM Evaluation Framework (Evals)**, and **Quality Assurance Gates** established for **Malabar Watch**.

---

## 1. Standard Software Engineering Practices

Malabar Watch adheres to standard cloud-native and software architecture principles:

### 1.1 The 12-Factor App Compliance Matrix

| 12-Factor Principle | Implementation in Malabar Watch |
|---|---|
| **I. Codebase** | Single git repository tracked in GitHub, deploying to Oracle Cloud environment. |
| **II. Dependencies** | Explicitly declared in `requirements.txt` with locked versions; isolated via Python `venv`. |
| **III. Config** | Strict separation of config from code via environment variables (`.env`, `src/config.py`). Secrets never committed. |
| **IV. Backing Services** | SQLite database, Open-Meteo API, Telegram API, and LLM endpoints treated as attached resources. |
| **V. Build, Release, Run** | Strict separation: GitHub Actions builds code ➔ releases artifact via Bastion tunnel ➔ systemd executes service. |
| **VI. Processes** | Stateless execution workers; persistent state cleanly delegated to SQLite database. |
| **VII. Port Binding** | N/A (Outbound-only long polling bot; no inbound port binding required). |
| **VIII. Concurrency** | Scaled via async event loop (`asyncio`) in Python for concurrent polling and API calls. |
| **IX. Disposability** | Fast startup (<1s) and graceful shutdown handling SIGTERM / SIGINT signals. |
| **X. Dev/Prod Parity** | 100% parity: local environment uses identical SQLite schemas, dry-run CLI flags, and Open-Meteo APIs. |
| **XI. Logs** | Structured JSON logging output to `stdout` (`structlog`), captured by systemd `journalctl`. |
| **XII. Admin Processes** | One-off administrative tasks (e.g. database migrations, dry-run backtests) run as CLI scripts. |

---

## 2. LLM Evaluation Framework (Evals)

Because LLMs generate natural language safety advisories, we implement a rigorous **Evaluation Suite (`tests/evals/`)** to benchmark LLM outputs before release.

```
┌─────────────────────────────────┐
│     Eval Suite Input Prompt     │  (Synthetic / Historical Test Cases)
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│     Resilient LLM Gateway       │  (Gemini / Groq)
└────────────────┬────────────────┘
                 │ Raw Generated JSON
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AUTOMATED EVALUATION CHECKS                     │
│                                                                        │
│  1. JSON Schema Validation     ➔ Is payload valid & complete?          │
│  2. Hallucination Guardrail    ➔ Does risk state match target level?  │
│  3. Malayalam Quality Metric   ➔ Valid script, proper terminology?     │
│  4. Safety Disclaimer Metric   ➔ Contains educational caution note?    │
│  5. Latency Benchmark          ➔ Response generated in < 5 seconds?    │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Automated Eval Test Metrics

| Metric ID | Metric Name | Pass Criteria / Threshold | Evaluation Method |
|---|---|---|---|
| **EVAL-1** | **JSON Structural Validity** | `100% Pass` | Schema assertion via `Pydantic` model parsing. |
| **EVAL-2** | **Risk Level Consistency** | `100% Pass` | Regex check enforcing that if risk level is `HIGH`, text must NOT contain phrases like "low risk" or "normal conditions". |
| **EVAL-3** | **Malayalam Script Coherence** | `> 95% Pass` | Unicode range validation ensuring Malayalam characters (`U+0D00` to `U+0D7F`) are present in `summary_ml` and `advisory_ml`. |
| **EVAL-4** | **Failover Latency Gate** | `< 5,000 ms` | Stopwatch timer measuring primary Gemini call and failover to Groq. |
| **EVAL-5** | **Safety Disclaimer Presence** | `100% Pass` | Assert string contains mandatory caution notice referencing official IMD / KSDMA alerts. |

---

## 3. Automated Code Quality & Testing Pipeline

### 3.1 Static Code Analysis & Linting

Before any code is committed or merged, automated quality tooling is executed:
- **Linter & Formatter (`ruff`):** Enforces PEP 8 standards, removes unused imports, and enforces modern Python 3.12 conventions.
- **Type Checking (`mypy`):** Strict static type verification across all modules.
- **Secret Scanning (`gitleaks`):** Scans git commit history for accidentally leaked API keys or bot tokens.

### 3.2 Automated Test Hierarchy (`pytest`)

```
tests/
├── unit/
│   ├── test_open_meteo_parser.py   # Test Open-Meteo JSON parsing & metric math
│   ├── test_risk_scorer.py         # Test deterministic threshold boundary logic
│   └── test_db_manager.py          # Test SQLite schema, inserts, and WAL operations
├── integration/
│   ├── test_llm_failover.py        # Test fallback from Gemini (simulated error) to Groq
│   └── test_telegram_dispatcher.py # Test long-polling dispatch & message formatting
└── evals/
    └── test_llm_evals.py           # Automated LLM quality & Malayalam coherence benchmarks
```

---

## 4. Operational Health & Observability Metrics

For production monitoring on Oracle Cloud ARM without adding third-party SaaS costs:

1. **Structured Log Telemetry (`structlog`):**
   Logs output in structured JSON format to standard output:
   ```json
   {
     "timestamp": "2026-08-15T10:30:00Z",
     "level": "info",
     "event": "risk_evaluated",
     "district": "wayanad",
     "r24h_mm": 142.5,
     "risk_level": "HIGH",
     "llm_provider": "gemini",
     "latency_ms": 1240
   }
   ```

2. **Systemd Watchdog & Automatic Recovery:**
   The `systemd` service monitors memory and process health. If the process crashes or exceeds RAM thresholds (e.g. >500MB), `systemd` automatically restarts the process within 5 seconds (`Restart=always`, `RestartSec=5s`).
