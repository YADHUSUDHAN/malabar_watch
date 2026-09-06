# Feature Spec: Deterministic Risk Scoring & Historical Disaster Context Engine

- **Spec ID**: `SPEC-002`
- **Status**: Implemented
- **Owner**: Malabar Watch Engineering
- **Target Release**: `v0.1.0`
- **Dependencies**: `SPEC-001` (Data Ingestion Engine), `SQLite Storage Engine`

---

## 1. Overview & Business Intent

In life-safety disaster warning systems, **numerical risk evaluation must be 100% deterministic, auditable, and mathematically reproducible**. Large Language Models (LLMs) must never be tasked with comparing multi-window precipitation thresholds directly due to prompt sensitivity and hallucination risks.

The **Deterministic Risk Scoring & Historical Context Engine** evaluates incoming hourly precipitation metrics against regional geotechnical thresholds for Kerala’s Western Ghats. It determines the discrete risk severity level (`LOW`, `MODERATE`, `HIGH`, `SEVERE`), identifies state transitions (escalation vs. sustained vs. downgrade) to eliminate alert fatigue, attaches verified historical precedent (such as Wayanad 2024 or Pettimudi 2020), and packages an immutable `RiskAssessment` payload for downstream AI advisory synthesis.

---

## 2. Multi-Tier Deterministic Risk Matrix

Risk levels are derived by evaluating trailing 24-hour ($R_{24\text{h}}$), 48-hour ($R_{48\text{h}}$), and Antecedent Precipitation Index ($API$) metrics against calibrated geotechnical thresholds:

| Level | Badge / Color | 24h Rainfall ($R_{24\text{h}}$) | 48h Rainfall ($R_{48\text{h}}$) | Soil Moisture Index ($API$) | Action / Alert Requirement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`LOW`** | 🟢 Green / ഹരിതം | $< 50\text{ mm}$ | $< 90\text{ mm}$ | $< 60$ | Routine hourly audit; no broadcast. |
| **`MODERATE`** | 🟡 Yellow / മഞ്ഞ | $50 – 100\text{ mm}$ | $90 – 150\text{ mm}$ | $60 – 100$ | Elevated risk advisory; caution near streams. |
| **`HIGH`** | 🟠 Orange / ഓറഞ്ച് | $100 – 200\text{ mm}$ | $150 – 250\text{ mm}$ | $100 – 150$ | Serious landslide threat; prepare evacuation. |
| **`SEVERE`** | 🔴 Red / ചുവപ്പ് | $\ge 200\text{ mm}$ | $\ge 250\text{ mm}$ | $\ge 150$ | Life safety emergency; matches historical disaster signatures. |

### Rule Precedence
1. The highest triggered severity tier among $R_{24\text{h}}$, $R_{48\text{h}}$, and $API$ dictates the final `risk_level`.
2. For example, if $R_{24\text{h}} = 65\text{ mm}$ (`MODERATE`) but $API = 155.0$ (`SEVERE`), the classification is strictly **`SEVERE`** because saturated laterite soil can fail under moderate rain.

---

## 3. State Transition & Alert Suppression Logic

To prevent spamming subscribers every hour when rainfall remains steady at the same risk tier, the engine evaluates **State Transitions**:

```
Previous Level ──▶ Current Level ──▶ Transition Evaluation
    LOW                 LOW          Sustained Low      ➔ No Alert
    LOW              MODERATE        Escalated          ➔ Dispatches Alert
  MODERATE             HIGH          Escalated          ➔ Dispatches Alert
    HIGH              SEVERE         Escalated          ➔ Dispatches Alert
    HIGH               HIGH          Sustained High     ➔ Dispatches Alert ONLY IF:
                                                          - Trailing 1h rain >= 25mm, OR
                                                          - Last alert was > 6 hours ago
   SEVERE             HIGH           Downgraded         ➔ Informational Update
```

### Transition States
- **`FIRST_ASSESSMENT`**: Initial run for a district without historical baseline. Dispatches alert if level $\ge$ `MODERATE`.
- **`ESCALATED`**: Risk level is strictly higher than previous assessment (`LOW` ➔ `MODERATE`, `MODERATE` ➔ `HIGH`, etc.). Always requires immediate alert dispatch.
- **`SUSTAINED`**: Risk level unchanged from previous run. Suppressed unless significant rainfall burst occurs ($\ge 25\text{ mm}/1\text{h}$) or 6-hour heartbeat cooldown expires.
- **`DOWNGRADED`**: Risk level decreases. Dispatches a recovery/downgrade advisory if moving down from `HIGH` or `SEVERE`.

---

## 4. Historical Regional Context Store

To ground the AI advisories in real historical memory, the engine includes a curated JSON dataset (`data/historical_events.json`):

```json
[
  {
    "event_id": "wayanad_2024",
    "district": "wayanad",
    "location": "Chooralmala / Mundakkai / Meppadi",
    "date": "July 2024",
    "rainfall_24h_mm": 348.0,
    "consequence": "Catastrophic debris flow across steep tea slopes, 250+ fatalities",
    "key_trigger": "Pre-saturated laterite soil overwhelmed by torrential single-day cloudburst",
    "analog_threshold_level": "SEVERE"
  },
  {
    "event_id": "idukki_2020",
    "district": "idukki",
    "location": "Pettimudi / Rajamala",
    "date": "August 2020",
    "rainfall_24h_mm": 210.0,
    "rainfall_48h_mm": 450.0,
    "consequence": "Massive hill collapse on plantation settlement, 66 fatalities",
    "key_trigger": "Sustained multi-day monsoonal downpour saturating steep granite interface",
    "analog_threshold_level": "SEVERE"
  },
  {
    "event_id": "kottayam_2021",
    "district": "kottayam",
    "location": "Koottickal / Teekoy",
    "date": "October 2021",
    "rainfall_24h_mm": 185.0,
    "consequence": "Flash floods, debris torrents, multiple river valley fatalities",
    "key_trigger": "Extreme short-duration cloudburst-like precipitation on Western Ghats foothills",
    "analog_threshold_level": "HIGH"
  }
]
```

When a risk assessment reaches `HIGH` or `SEVERE`, the engine matches and attaches the most relevant historical event to provide historical grounding for the LLM prompt.

---

## 5. User Stories & Acceptance Criteria

- **US-1 (Deterministic Scoring)**: As the monitoring agent, I need to evaluate precipitation metrics without calling an LLM so that risk classification is mathematically guaranteed and never hallucinates.
- **US-2 (Alert Filtering)**: As a Telegram subscriber, I only want alerts when risk escalates, significant new rain falls, or during major status changes so that I do not experience alert fatigue.
- **US-3 (Historical Grounding)**: As an early-warning reader, I want regional historical disaster comparisons so that the urgency of the warning is immediately understood.

### Detailed Acceptance Criteria
- [x] **AC-1 (Scoring Rules)**: Implement `evaluate_metrics(metrics: PrecipitationMetrics) -> RiskAssessment` strictly adhering to the 4-tier matrix ($R_{24\text{h}}, R_{48\text{h}}, API$).
- [x] **AC-2 (Rule Auditing)**: Every assessment must record human-readable `triggered_rules` explaining exactly why the level was assigned (e.g. `["24h rainfall (162.0mm) >= 100.0mm", "API index (112.5) >= 100.0"]`).
- [x] **AC-3 (State Transitions)**: Query the latest assessment from SQLite, compare against the new result, and calculate `EscalationState` (`FIRST_ASSESSMENT`, `ESCALATED`, `SUSTAINED`, `DOWNGRADED`).
- [x] **AC-4 (Historical Context Store)**: Package and load `data/historical_events.json`. Attach matching historical precedent for `HIGH` and `SEVERE` states.
- [x] **AC-5 (Database Persistence)**: Create table `risk_assessments` in SQLite and implement `save_assessment` and `get_latest_assessment`.
- [x] **AC-6 (CLI Verification)**: Add `malabar-watch --test-risk` CLI command that runs risk evaluation on live or synthetic metrics and outputs formatted Rich tables.

---

## 6. Technical & System Architecture

### 6.1 Package Layout (`src/malabar_watch/risk_engine/`)

```
src/malabar_watch/risk_engine/
├── __init__.py           # Public exports: evaluate_risk, RiskEvaluator, models
├── models.py             # Enums: RiskLevel, EscalationState; Models: RiskAssessment, HistoricalEvent
├── evaluator.py          # Deterministic rule evaluation and threshold logic
├── historical.py         # Historical precedent loader and district/severity matcher
└── service.py            # RiskAssessmentService: Ingest metrics -> Evaluate -> Check Transition -> Save
```

### 6.2 Target SQLite Schema (`risk_assessments`)

```sql
CREATE TABLE IF NOT EXISTS risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    assessed_at DATETIME NOT NULL,
    risk_level TEXT NOT NULL,
    escalation_state TEXT NOT NULL,
    rainfall_1h REAL NOT NULL,
    rainfall_24h REAL NOT NULL,
    rainfall_48h REAL NOT NULL,
    rainfall_72h REAL NOT NULL,
    antecedent_index REAL NOT NULL,
    triggered_rules TEXT NOT NULL, -- JSON array of strings
    historical_event_id TEXT,
    requires_alert INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. Edge Cases & Risk Mitigation

| Failure Mode / Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **No Prior Assessment Exists** | Cannot determine delta transition. | Treat as `FIRST_ASSESSMENT`. Require alert if level $\ge$ `MODERATE`. |
| **Borderline Threshold Hovering** | $R_{24\text{h}}$ oscillates around 100mm (e.g. 99.8 ➔ 100.2 ➔ 99.9). | Implement hysteresis: require risk downgrade to persist below threshold for 2 consecutive hours before dropping alert tier. |
| **Missing Historical Match** | District has no historical entry. | Gracefully return `historical_precedent = None` without crashing. |
| **Zero Rain Baseline** | $R_{24\text{h}} = 0.0, API = 0.0$. | Classified cleanly as `LOW` with empty triggered rules. |

---

## 8. Verification & Test Criteria

### 8.1 Automated Tests
- **Unit Tests (`tests/unit/test_risk_evaluator.py`)**:
  - Test all 4 severity tiers (`LOW`, `MODERATE`, `HIGH`, `SEVERE`) across single and multi-variable triggers.
  - Test $API$-dominant trigger (low rain but saturated soil).
  - Test triggered rule audit explanations.
- **Unit Tests (`tests/unit/test_historical_context.py`)**:
  - Test historical dataset loading and validation.
  - Test district and severity matching.
- **Integration Tests (`tests/integration/test_risk_storage.py`)**:
  - Test end-to-end flow from `PrecipitationMetrics` to persisted `risk_assessments` in SQLite.
  - Test state transitions: escalation, sustained suppression, and downgrades.

### 8.2 CLI Verification Command
```bash
# Run risk engine test suite
uv run pytest tests/ -k "risk"

# Run CLI risk evaluation
uv run malabar-watch --test-risk
```
