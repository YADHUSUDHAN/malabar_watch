# Feature Spec: Open-Meteo Weather Data Ingestion Engine

- **Spec ID**: `SPEC-001`
- **Status**: Implemented
- **Owner**: Malabar Watch Engineering
- **Target Release**: `v0.1.0`
- **Dependencies**: SQLite Storage Engine (`src/malabar_watch/storage/`)

---

## 1. Overview & Business Intent

**Malabar Watch** requires accurate, timely, and hyper-local precipitation metrics to detect early signatures of catastrophic slope failures in Kerala’s Western Ghats. The **Data Ingestion Engine** is the foundational upstream service of the autonomous pipeline. It queries the Open-Meteo Weather API hourly, extracts granular precipitation metrics for vulnerable micro-zones in Wayanad, Idukki, and Kottayam, calculates rolling cumulative metrics and soil moisture decay indices, and persists normalized records into SQLite (WAL mode).

---

## 2. Target Micro-Zone Coordinates & Configuration

Rather than using generic district centroids, queries target specific steep-slope micro-zones prone to debris flows:

| District ID | District Name | Representative Micro-Zone | Latitude (°N) | Longitude (°E) | Vulnerability Context |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `wayanad` | Wayanad | Vythiri / Meppadi / Chooralmala | `11.6084` | `76.0883` | Extreme steep slope debris flows (2024 disaster epicenter) |
| `idukki` | Idukki | Munnar / Devikulam / Pettimudi | `10.0889` | `77.0595` | High-elevation tea plantation slope failures (2020 Pettimudi) |
| `kottayam` | Kottayam | Teekoy / Erattupetta / Kanjirappally | `9.6896` | `76.8160` | Foothill flash floods & torrential debris surges |

---

## 3. User Stories & Functional Requirements

- **US-1 (Hourly Polling)**: As the monitoring agent, I need to fetch hourly precipitation for the 3 target districts without requiring API keys or incurring recurring costs.
- **US-2 (Derived Cumulative Metrics)**: As the risk evaluation engine, I need rolling cumulative metrics ($R_{1\text{h}}$, $R_{24\text{h}}$, $R_{48\text{h}}$, $R_{72\text{h}}$) and the Antecedent Precipitation Index ($API$) computed deterministically.
- **US-3 (Database Persistence)**: As the historical audit layer, I need every hourly reading and derived metric stored cleanly in SQLite with WAL mode enabled.
- **US-4 (Resilient Failover & Offline Fallback)**: As an unattended background worker, I need exponential backoff retries on network blips and graceful handling of empty or malformed API responses.

### Detailed Acceptance Criteria
- [x] **AC-1 (HTTP Client)**: Implement an asynchronous `OpenMeteoClient` using `httpx.AsyncClient` with custom timeout (10s) and exponential backoff retry.
- [x] **AC-2 (Query Parameters)**: Formulate Open-Meteo queries requesting `hourly=precipitation,rain,showers`, `timezone=Asia/Kolkata`, `past_days=3`, and `forecast_days=1`.
- [x] **AC-3 (Metric Calculations)**:
  - $R_{1\text{h}}$: Precipitation in the most recent completed hour.
  - $R_{24\text{h}}$: Sum of precipitation across the trailing 24 hours.
  - $R_{48\text{h}}$: Sum of precipitation across the trailing 48 hours.
  - $R_{72\text{h}}$: Sum of precipitation across the trailing 72 hours.
  - $API_t$: Antecedent Precipitation Index computed as $API_t = P_t + \alpha \cdot API_{t-1}$ with decay factor $\alpha = 0.85$.
- [x] **AC-4 (Data Transfer Models)**: Implement strongly-typed Pydantic models: `DistrictTarget`, `HourlyPrecipitationData`, `PrecipitationMetrics`.
- [x] **AC-5 (Storage Integration)**: Insert hourly observations into SQLite `rainfall_observations` table using parameter binding to prevent SQL injection.
- [x] **AC-6 (CLI Dry-Run)**: Add CLI verification command (`malabar-watch test-ingest`) to test live and mock ingestion from the terminal.

---

## 4. Technical & System Architecture

### 4.1 Component Design (`src/malabar_watch/ingestion/`)

```
src/malabar_watch/ingestion/
├── __init__.py          # Public exports: OpenMeteoClient, IngestionService, DistrictTarget
├── client.py            # Async HTTP client with backoff retries using httpx
├── models.py            # Pydantic schemas (DistrictTarget, IngestionResult, Metrics)
├── metrics.py           # Pure mathematical functions for R1h, R24h, R48h, R72h, and API
└── service.py           # IngestionService coordinating fetch -> calculate -> persist
```

### 4.2 Data Contracts & Pydantic Schemas

```python
class DistrictTarget(BaseModel):
    district_id: str
    name: str
    micro_zone: str
    latitude: float
    longitude: float


class HourlyPrecipitationData(BaseModel):
    timestamps: list[datetime]
    precipitation: list[float]


class PrecipitationMetrics(BaseModel):
    district_id: str
    timestamp: datetime
    rainfall_1h: float
    rainfall_24h: float
    rainfall_48h: float
    rainfall_72h: float
    antecedent_index: float
```

### 4.3 SQLite Target Schema (`rainfall_observations`)

```sql
CREATE TABLE IF NOT EXISTS rainfall_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    precipitation_mm REAL NOT NULL,
    rainfall_24h REAL NOT NULL DEFAULT 0.0,
    rainfall_48h REAL NOT NULL DEFAULT 0.0,
    rainfall_72h REAL NOT NULL DEFAULT 0.0,
    antecedent_index REAL NOT NULL DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(district, timestamp) ON CONFLICT REPLACE
);
```

---

## 5. Edge Cases & Risk Mitigation

| Failure Mode / Edge Case | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Open-Meteo HTTP 5xx / Timeout** | Ingestion pipeline fails for the current hour. | Exponential backoff (3 retries: 2s, 4s, 8s). If still failing, log warning and use last cached database record. |
| **Missing Timestamps or Nulls** | Potential `TypeError` during summation. | Sanitizer validates data array; replace `None` or negative values with `0.0`. |
| **Out-of-Order Readings** | Faulty rolling sum calculation. | Explicitly sort hourly arrays by timestamp ascending before windowing. |
| **Zero Rain Across 72 Hours** | Math edge cases (e.g. division by zero). | Explicit test cases verifying $API$ decays gracefully to 0.0 without errors. |
| **Clock/Timezone Desync** | Mismatched timestamps between local clock and API. | Enforce UTC or explicit `Asia/Kolkata` datetime objects throughout ingestion models. |

---

## 6. Verification & Test Criteria

### 6.1 Automated Test Suite
- **Unit Tests (`tests/unit/test_ingestion.py`)**:
  - Test HTTP query parameter generation.
  - Test metric computations ($R_{1\text{h}}, R_{24\text{h}}, R_{48\text{h}}, R_{72\text{h}}, API$) against known deterministic fixture data.
  - Test handling of null, missing, and negative precipitation values.
- **Integration Tests (`tests/integration/test_ingestion_storage.py`)**:
  - Test end-to-end flow with mocked Open-Meteo JSON payload written to in-memory SQLite (`:memory:`).
  - Test deduplication via `UNIQUE(district, timestamp) ON CONFLICT REPLACE`.

### 6.2 Manual & CLI Verification Command
```bash
# Run unit & integration test coverage for ingestion
uv run pytest tests/ -k "ingestion"

# Run live CLI dry-run test
uv run malabar-watch test-ingest
```
