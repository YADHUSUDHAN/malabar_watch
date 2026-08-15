# Malabar Watch (മലബാർ വാച്ച്)
### AI-Powered Rainfall & Landslide Early-Warning Agent for Kerala
**Master Solution Architecture & Technical Design Blueprint**

Version: 2.0 · Date: August 2026  
Status: Planning & Architectural Design Phase

---

## 1. Executive Summary & Vision

**Malabar Watch** is a self-hosted, near-zero-cost AI agent designed to ingest live rainfall data for landslide-vulnerable districts in Kerala (Wayanad, Idukki, Kottayam, and expanding), reason over high-resolution precipitation metrics against historical risk thresholds and disaster case studies, and automatically dispatch structured, bilingual (English + Malayalam) plain-language early warnings to subscribers over Telegram.

### Motivation & Context
Kerala’s Western Ghats region experiences severe seasonal monsoons leading to catastrophic slope failures and debris flows. Recent disasters—such as the **2024 Wayanad Landslides (Chooralmala & Mundakkai)** with over 250 casualties, the **2020 Pettimudi (Idukki) landslide**, and the **2026 central/southern flood and landslide emergency**—demonstrate that generic, district-wide alerts often fail to communicate localized, plain-language urgency to communities.

Malabar Watch bridges this gap by combining:
1. High-resolution hourly precipitation data from **Open-Meteo**.
2. Deterministic multi-day cumulative risk scoring.
3. Resilient dual-LLM intelligence (**Google Gemini API primary**, **Groq API fallback**) to generate accessible, bilingual alerts.
4. **Zero-recurring-cost cloud infrastructure** provisioned on GCP Compute Engine Always Free Tier (`e2-micro`, 0.25-2 vCPU, 1 GB RAM, 30 GB disk, 2 GB Swap).
5. **Zero-trust, zero-exposed-inbound-port security architecture**.

---

## 2. System Architecture Topology

```
                               ┌───────────────────────────────────────────────┐
                               │       Open-Meteo High-Res Weather API         │
                               │   (Hourly precipitation, rain, showers in mm) │
                               └───────────────────────┬───────────────────────┘
                                                       │ Outbound HTTPS Pull (Hourly)
                                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           MALABAR WATCH ENGINE (GCP Compute Engine Always Free)                         │
│                                                                                                         │
│  ┌──────────────────────────────┐          ┌────────────────────────────────────────────────────────┐  │
│  │   Data Ingestion Engine      │─────────▶│                SQLite Storage (WAL Mode)                │  │
│  │  (Wayanad, Idukki, Kottayam) │          │  - Raw Rainfall Readings   - Alert Log                 │  │
│  └──────────────────────────────┘          │  - Risk Assessments        - Subscribers DB            │  │
│                                            └───────────────────────────┬────────────────────────────┘  │
│                                                                        │                               │
│                                                                        ▼                               │
│                                            ┌────────────────────────────────────────────────────────┐  │
│                                            │                  Risk Scoring Engine                   │  │
│                                            │  - Rolling 24h, 48h, 72h totals                        │  │
│                                            │  - Antecedent Precipitation Index (API)                │  │
│                                            └───────────────────────────┬────────────────────────────┘  │
│                                                                        │                               │
│                                                                        ▼                               │
│                                            ┌────────────────────────────────────────────────────────┐  │
│                                            │             Resilient Dual-LLM Gateway                 │  │
│                                            │   ┌────────────────────────────────────────────────┐   │  │
│                                            │   │ Primary: Google Gemini API (gemini-2.5-flash)  │   │  │
│                                            │   └───────────────────────┬────────────────────────┘   │  │
│                                            │                           │ Failover (>10s / 429/ 5xx) │  │
│                                            │   ┌───────────────────────▼────────────────────────┐   │  │
│                                            │   │ Fallback: Groq API (llama-3.3-70b-versatile)   │   │  │
│                                            │   └────────────────────────────────────────────────┘   │  │
│                                            └───────────────────────────┬────────────────────────────┘  │
│                                                                        │                               │
│                                                                        ▼                               │
│                                            ┌────────────────────────────────────────────────────────┐  │
│                                            │              Bilingual Telegram Bot Engine             │  │
│                                            │  - Outbound Long-Polling (/status, /subscribe)          │  │
│                                            │  - Push Alerts (English + Malayalam)                   │  │
│                                            └───────────────────────────┬────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┼────────────────────────────────┘
                                                                         │ Outbound HTTPS Polling/Push
                                                                         ▼
                                                         ┌────────────────────────────────┐
                                                         │     Telegram Messenger App     │
                                                         │  (Subscribers / Public Channel)│
                                                         └────────────────────────────────┘
```

---

## 3. High-Level Technology Stack & Cost Matrix

| Layer | Choice | Technical Rationale | Recurring Cost |
|---|---|---|---|
| **Compute / OS** | GCP Compute Engine Always Free (`e2-micro`, 0.25-2 vCPU, 1 GB RAM, 30 GB Disk + 2 GB Swap) / Ubuntu 24.04 LTS | Permanent free-forever cloud VM available globally | **₹0 / month** |
| **IaC & Security** | Terraform + GCP VPC Firewall Rules | Keyless, zero-inbound SSH ports, reproducible setup | **₹0 / month** |
| **Data Provider** | Open-Meteo API | Free, high-resolution hourly precipitation, no API key needed | **₹0 / month** |
| **Primary LLM** | Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`) | Generous free tier rate limits (15 RPM / 1M TPM), excellent bilingual capability | **₹0 / month** |
| **Fallback LLM** | Groq API (`llama-3.3-70b-versatile`) | Ultra-fast inferencing free tier (30 RPM / 14.4k RPD), reliable backup | **₹0 / month** |
| **Storage** | SQLite 3 (WAL Mode enabled) | File-based, zero-maintenance, handles 100k+ records easily | **₹0 / month** |
| **Bot Framework** | `python-telegram-bot` (Async) | Long-polling outbound connection; no exposed inbound ports | **₹0 / month** |
| **CI/CD** | GitHub Actions + OIDC | Keyless deployment pipeline directly from git repository | **₹0 / month** |
| **Total Cost** | | | **₹0 / month** |

---

## 4. Key Architectural Pillars

### 4.1 Data Ingestion & Micro-Zone Coordinates
Open-Meteo fetches hourly precipitation for representative coordinates:
- **Wayanad (Vythiri / Chooralmala belt):** `11.6084° N, 76.0883° E`
- **Idukki (Munnar / Devikulam slope):** `10.0889° N, 77.0595° E`
- **Kottayam (Teekoy / Erattupetta hilly zone):** `9.6896° N, 76.8160° E`

### 4.2 Multi-Tier Deterministic Risk Model
To prevent hallucination in risk scoring, numerical scoring is strictly computed deterministically before passing metrics to the LLM:
$$API_t = P_t + k \cdot API_{t-1} \quad (k = 0.85)$$
Where $P_t$ is daily precipitation and $k$ is the decay factor representing soil drainage.

- **Low (Green / ഹരിതം):** < 50mm / 24h
- **Moderate (Yellow / മഞ്ഞ):** 50 – 100mm / 24h, or 90 – 150mm / 48h
- **High (Orange / ഓറഞ്ച്):** 100 – 200mm / 24h, or 150 – 250mm / 48h
- **Severe (Red / ചുവപ്പ്):** > 200mm / 24h, or > 250mm / 48h, or $API > \text{threshold}$ (Corresponds to historical landslide triggers like Wayanad 2024).

### 4.3 Dual-Provider LLM Gateway (Gemini + Groq)
- Generates bilingual plain-language warnings (English + Malayalam).
- If Gemini fails (timeout > 10s, rate limit 429, or server error 5xx), the system seamlessly switches to Groq (`llama-3.3-70b-versatile`).

### 4.4 Outbound-Only Telegram Bot Architecture
- Uses Telegram long polling (`getUpdates`).
- No public open ports (`0.0.0.0`) on the VM.
- Supports `/status <district>`, `/subscribe <district>`, `/unsubscribe`, `/history`, and `/disclaimer`.

---

## 5. Repository Documentation Structure

The documentation for this project is organized under the [`docs/`](file:///d:/projects/malabar_watch/docs) directory:
- [`docs/ARCHITECTURE.md`](file:///d:/projects/malabar_watch/docs/ARCHITECTURE.md) - Full technical architecture specification.
- [`docs/DATA_INGESTION_SPEC.md`](file:///d:/projects/malabar_watch/docs/DATA_INGESTION_SPEC.md) - Open-Meteo integration & calculations.
- [`docs/RISK_MODEL_SPEC.md`](file:///d:/projects/malabar_watch/docs/RISK_MODEL_SPEC.md) - Risk threshold matrix & historical event context.
- [`docs/LLM_PROMPT_ENGINEERING.md`](file:///d:/projects/malabar_watch/docs/LLM_PROMPT_ENGINEERING.md) - Gemini/Groq prompt engineering & JSON schema.
- [`docs/TELEGRAM_BOT_GUIDE.md`](file:///d:/projects/malabar_watch/docs/TELEGRAM_BOT_GUIDE.md) - Telegram bot setup, commands & BotFather guide.
- [`docs/INFRA_AND_SECURITY.md`](file:///d:/projects/malabar_watch/docs/INFRA_AND_SECURITY.md) - GCP Compute Engine Always Free, Terraform & GitHub Actions CI/CD.
- [`docs/DISCLAIMER.md`](file:///d:/projects/malabar_watch/docs/DISCLAIMER.md) - Project disclaimer & safety guidelines.
