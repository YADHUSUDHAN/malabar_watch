# Feature Spec: Open-Meteo Weather Data Ingestion

- **Spec ID**: `SPEC-001`
- **Status**: Approved
- **Owner**: Malabar Watch Engineering
- **Target Release**: `v0.1.0`

---

## 1. Overview & Business Intent

The Open-Meteo Data Ingestion worker is responsible for polling hourly precipitation metrics across target Kerala districts (Wayanad, Idukki, Kottayam) every 60 minutes. The extracted metrics are normalized and saved to SQLite database storage for downstream risk score calculation.

---

## 2. User Stories & Functional Requirements

- **US-1**: As a risk monitoring engine, I need hourly rainfall data (past 72 hours) so that I can compute rolling cumulative metrics ($24\text{h}, 48\text{h}, 72\text{h}$) and Antecedent Precipitation Index ($API$).
- **US-2**: As a production system, I need zero API keys and resilient HTTP retry logic so that weather data collection never fails due to temporary network blips.

### Detailed Acceptance Criteria
- [ ] Query Open-Meteo API endpoint for Vythiri (`11.55, 76.04`), Munnar (`10.08, 77.06`), and Teekoy (`9.68, 76.82`).
- [ ] Calculate cumulative 24h precipitation ($P_{24}$).
- [ ] Compute Antecedent Precipitation Index using $API_t = P_t + \alpha \cdot API_{t-1}$ with decay factor $\alpha = 0.85$.
- [ ] Store normalized observations in SQLite `rainfall_observations` table with WAL mode enabled.

---

## 3. Data Schema & Contracts

### Open-Meteo API Payload Format
```json
{
  "latitude": 11.55,
  "longitude": 76.04,
  "hourly": {
    "time": ["2026-08-15T00:00", "2026-08-15T01:00"],
    "precipitation": [0.0, 12.4]
  }
}
```

---

## 4. Verification Plan

```bash
uv run pytest tests/unit/test_config.py tests/integration/test_storage.py
```
