# Risk Model Specification - Multi-Tier Threshold Engine

This document defines the deterministic risk evaluation matrix and historical disaster context rules used by **Malabar Watch**.

---

## 1. Risk Evaluation Philosophy

In disaster early warning systems, **LLMs should never perform threshold classification directly**, as LLMs can hallucinate numerical comparisons (e.g. incorrectly judging 140mm as <100mm).

Therefore, **Malabar Watch** splits responsibility:
1. **Deterministic Risk Engine (`scorer.py`):** Calculates exact metrics and classifies the risk level into discrete enum states (`LOW`, `MODERATE`, `HIGH`, `SEVERE`).
2. **LLM Engine (`summarizer.py`):** Takes the deterministic risk level, rainfall metrics, and historical precedents to synthesize natural, bilingual human language summaries.

---

## 2. Rainfall Risk Scoring Matrix

Risk levels are determined by evaluating cumulative rainfall against configured thresholds:

```yaml
# thresholds.yaml
districts:
  wayanad:
    low: { r24h: 50.0, r48h: 90.0 }
    moderate: { r24h: 100.0, r48h: 150.0 }
    high: { r24h: 200.0, r48h: 250.0 }
    severe: { r24h: 250.0, r48h: 350.0 }
```

### Classification Rules

| Level | Color Code | 24h Rainfall ($R_{24\text{h}}$) | 48h Rainfall ($R_{48\text{h}}$) | Saturation ($API$) | Action Required |
|---|---|---|---|---|---|
| **LOW** | 🟢 Green / ഹരിതം | < 50 mm | < 90 mm | Normal | Routine hourly logging. |
| **MODERATE** | 🟡 Yellow / മഞ്ഞ | 50 – 100 mm | 90 – 150 mm | Elevated | Notify subscribers. Advise caution around streams. |
| **HIGH** | 🟠 Orange / ഓറഞ്ച് | 100 – 200 mm | 150 – 250 mm | Saturated | High risk alert. Advise preparing for evacuation in steep slope zones. |
| **SEVERE** | 🔴 Red / ചുവപ്പ് | > 200 mm | > 250 mm | Fully Saturated | Extreme warning. Match historical landslide triggers. Relocate immediately. |

---

## 3. Historical Event Context Dataset (`historical_events.json`)

To ground AI alerts in real regional history, the system injects relevant historical event context when risk levels reach `HIGH` or `SEVERE`:

```json
[
  {
    "event_id": "wayanad_2024",
    "district": "wayanad",
    "location": "Chooralmala / Mundakkai",
    "date": "July 2024",
    "24h_rainfall_mm": 348.0,
    "antecedent_days": 5,
    "consequence": "Massive debris flow and slope failure, 250+ fatalities",
    "key_trigger": "Extreme single-day rainfall over pre-saturated laterite soil"
  },
  {
    "event_id": "idukki_2020",
    "district": "idukki",
    "location": "Pettimudi / Rajamala",
    "date": "August 2020",
    "24h_rainfall_mm": 210.0,
    "48h_rainfall_mm": 450.0,
    "consequence": "Tea plantation worker settlement overwhelmed by hill slip, 66 fatalities",
    "key_trigger": "Prolonged multi-day continuous heavy rainfall"
  },
  {
    "event_id": "kottayam_2021",
    "district": "kottayam",
    "location": "Koottickal / Teekoy",
    "date": "October 2021",
    "24h_rainfall_mm": 185.0,
    "consequence": "Flash floods and sudden hillside torrents",
    "key_trigger": "High-intensity short-duration cloudburst-like event"
  }
]
```
