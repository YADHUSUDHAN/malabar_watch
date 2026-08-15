# Data Ingestion Specification - Open-Meteo Integration

This document defines the technical specification for fetching rainfall data using the **Open-Meteo API** for Malabar Watch.

---

## 1. Data Provider Overview
**Open-Meteo** provides high-resolution open weather data derived from national weather services (ECMWF, DWD, GFS). It requires **no API key** and has generous rate limits suitable for hourly polling.

- **Base Endpoint:** `https://api.open-meteo.com/v1/forecast`
- **Response Format:** JSON
- **Polling Frequency:** Hourly (at minute :05 to ensure full hour data availability)

---

## 2. Configured Target Micro-Zones (Kerala Districts)

| District | Target Micro-Zone / Slope | Latitude (°N) | Longitude (°E) | Vulnerability Context |
|---|---|---|---|---|
| **Wayanad** | Vythiri / Meppadi / Chooralmala | `11.6084` | `76.0883` | Extreme steep slope debris flows (Site of 2024 disaster) |
| **Idukki** | Munnar / Devikulam / Peerumade | `10.0889` | `77.0595` | High elevation tea-plantation soil slips (Site of 2020 Pettimudi event) |
| **Kottayam** | Teekoy / Erattupetta / Kanjirappally | `9.6896` | `76.8160` | Western Ghats foothill flash floods & debris torrents |

---

## 3. Query Parameter Specification

For each district, the HTTP request is constructed as follows:

```http
GET /v1/forecast?latitude=11.6084&longitude=76.0883&hourly=precipitation,rain,showers&timezone=Asia%2FKolkata&past_days=3&forecast_days=1 HTTP/1.1
Host: api.open-meteo.com
Accept: application/json
```

### Response Mapping
The API returns hourly precipitation arrays:
```json
{
  "latitude": 11.6084,
  "longitude": 76.0883,
  "timezone": "Asia/Kolkata",
  "hourly": {
    "time": ["2026-08-14T00:00", "2026-08-14T01:00", "..."],
    "precipitation": [0.0, 12.4, 25.1, 40.2, "..."]
  }
}
```

---

## 4. Calculated Derived Metrics

From the raw hourly precipitation vector $P = [p_0, p_1, \dots, p_{n}]$, the ingestion worker computes:

1. **1-Hour Intensity ($R_{1\text{h}}$):**  
   $$R_{1\text{h}} = p_{\text{latest}}$$

2. **24-Hour Cumulative Rainfall ($R_{24\text{h}}$):**  
   $$R_{24\text{h}} = \sum_{i=n-23}^{n} p_i$$

3. **48-Hour Cumulative Rainfall ($R_{48\text{h}}$):**  
   $$R_{48\text{h}} = \sum_{i=n-47}^{n} p_i$$

4. **72-Hour Cumulative Rainfall ($R_{72\text{h}}$):**  
   $$R_{72\text{h}} = \sum_{i=n-71}^{n} p_i$$

5. **Antecedent Precipitation Index ($API$):**  
   $$API_t = P_t + k \cdot API_{t-1}$$  
   Where $k = 0.85$ (decay coefficient simulating daily soil moisture loss in Western Ghats laterite soil).

---

## 5. Resilience & Fallback Handling

- **Request Timeout:** 10 seconds per district fetch.
- **Retry Policy:** 3 exponential backoff attempts (2s, 4s, 8s).
- **Graceful Failure:** If Open-Meteo is temporarily unreachable, the system uses stored past hourly readings from SQLite to compute cumulative metrics up to the last successful poll, logging a warning status.
