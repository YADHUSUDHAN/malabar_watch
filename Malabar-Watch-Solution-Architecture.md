# Malabar Watch (മലബാർ വാച്ച്)
### AI-Powered Rainfall & Landslide Early-Warning Agent for Kerala
**Master Solution Architecture & Technical Design Blueprint**

Version: 2.1 · Date: September 2026  
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
4. **Near-zero-cost cloud infrastructure** on **Amazon Web Services (AWS)** Free Tier (`t2.micro` / `t3.micro`, 1 vCPU, 1 GB RAM, 30 GB EBS gp3 disk, 2 GB Linux Swap) located in `ap-south-1` (Mumbai) for low-latency delivery.
5. **Zero-trust, zero-exposed-inbound-port security architecture** utilizing AWS Security Groups and **AWS Systems Manager (SSM) Session Manager** for keyless administration without public SSH.
6. **Strict Two-Stage Execution Lifecycle**: Complete local execution and end-to-end verification first; cloud deployment only after local validation is 100% complete.

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
│                      MALABAR WATCH ENGINE (AWS EC2 Free Tier - ap-south-1 Mumbai)                      │
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
| **Compute / OS** | AWS EC2 (`t2.micro` / `t3.micro`, 1 vCPU, 1 GB RAM, 30 GB EBS gp3 + 2 GB Swap) / Ubuntu 24.04 LTS (`ap-south-1`) | 750 hrs/month AWS 12-Month Free Tier, low network latency to Kerala users | **₹0 / month** (Free Tier) |
| **IaC & Security** | Terraform (`hashicorp/aws`) + AWS Security Groups + AWS SSM | Zero inbound application ports, keyless SSM Session Manager access | **₹0 / month** |
| **Data Provider** | Open-Meteo API | Free, high-resolution hourly precipitation, no API key needed | **₹0 / month** |
| **Primary LLM** | Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`) | Generous free tier rate limits (15 RPM / 1M TPM), excellent bilingual capability | **₹0 / month** |
| **Fallback LLM** | Groq API (`llama-3.3-70b-versatile`) | Ultra-fast inferencing free tier (30 RPM / 14.4k RPD), reliable backup | **₹0 / month** |
| **Storage** | SQLite 3 (WAL Mode enabled) | File-based, zero-maintenance, handles 100k+ records easily | **₹0 / month** |
| **Bot Framework** | `python-telegram-bot` (Async) | Long-polling outbound connection; no exposed inbound ports | **₹0 / month** |
| **CI/CD** | GitHub Actions + AWS OIDC Workload Identity | Keyless deployment pipeline directly from git repository | **₹0 / month** |
| **Total Cost** | | | **₹0 / month** |

---

## 4. Two-Stage Execution Lifecycle: Local-First to AWS Cloud

To guarantee stability, minimize unexpected cloud costs, and eliminate configuration bugs before cloud deployment, Malabar Watch strictly adheres to a **Two-Stage Execution Lifecycle**:

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ STAGE 1: LOCAL-FIRST DEVELOPMENT & COMPREHENSIVE VERIFICATION           │
 │                                                                         │
 │  1. Local Environment Setup (Python 3.12/3.13, uv, SQLite local file)   │
 │  2. Data Ingestion Test (Open-Meteo live pull + mock fixture fallback)  │
 │  3. Deterministic Scorer & Risk Math Validation (Edge cases & scenarios)│
 │  4. Dual-LLM Gateway Verification (Gemini primary -> Groq failover)     │
 │  5. Interactive Telegram Bot Testing (Local long-polling, test chats)   │
 │  6. Full Test Suite & Evals (`pytest`, `mypy`, `ruff`, CLI dry-runs)    │
 └────────────────────────────────────┬────────────────────────────────────┘
                                      │ All local verifications pass 100%
                                      ▼
 ┌─────────────────────────────────────────────────────────────────────────┐
 │ STAGE 2: AWS CLOUD PROVISIONING & PRODUCTION DEPLOYMENT                 │
 │                                                                         │
 │  1. Terraform AWS Provisioning (VPC, Security Group, IAM SSM Role, EC2) │
 │  2. Keyless Remote Access via AWS Systems Manager (No open port 22)     │
 │  3. Host Hardening (Ubuntu 24.04, 2GB Swap, non-root service user)      │
 │  4. Automated GitHub Actions CI/CD with AWS OIDC Web Identity           │
 │  5. Production Verification & Continuous Health Monitoring              │
 └─────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Stage 1: Local Development & Verification
1. **Local Pipeline Execution**: Run data ingestion, risk calculation, LLM prompt formatting, and SQLite persistence completely locally.
2. **Local Bot Long-Polling**: Launch `python-telegram-bot` in long-polling mode against Telegram API directly from the workstation without needing public IP or port forwarding.
3. **Automated Quality Gates**: Enforce `uv run pytest`, `uv run mypy src`, and `uv run ruff check .` locally before pushing code.

### 4.2 Stage 2: Seamless Transition to AWS Cloud
1. **Infrastructure as Code**: Apply Terraform manifests to create AWS EC2 instance in `ap-south-1`, Security Group (zero inbound), and IAM role for SSM.
2. **Keyless Administration**: Connect to the EC2 host via AWS SSM Session Manager (`aws ssm start-session --target <instance-id>`).
3. **Process Supervision**: Deploy Malabar Watch as a `systemd` service running under a dedicated unprivileged user (`malabarwatch`).

---

## 5. Key Architectural Pillars

### 5.1 Data Ingestion & Micro-Zone Coordinates
Open-Meteo fetches hourly precipitation for representative coordinates:
- **Wayanad (Vythiri / Chooralmala belt):** `11.6084° N, 76.0883° E`
- **Idukki (Munnar / Devikulam slope):** `10.0889° N, 77.0595° E`
- **Kottayam (Teekoy / Erattupetta hilly zone):** `9.6896° N, 76.8160° E`

### 5.2 Multi-Tier Deterministic Risk Model
To prevent hallucination in risk scoring, numerical scoring is strictly computed deterministically before passing metrics to the LLM:
$$API_t = P_t + k \cdot API_{t-1} \quad (k = 0.85)$$
Where $P_t$ is daily precipitation and $k$ is the decay factor representing soil drainage.

- **Low (Green / ഹരിതം):** < 50mm / 24h
- **Moderate (Yellow / മഞ്ഞ):** 50 – 100mm / 24h, or 90 – 150mm / 48h
- **High (Orange / ഓറഞ്ച്):** 100 – 200mm / 24h, or 150 – 250mm / 48h
- **Severe (Red / ചുവപ്പ്):** > 200mm / 24h, or > 250mm / 48h, or $API > \text{threshold}$ (Corresponds to historical landslide triggers like Wayanad 2024).

### 5.3 Dual-Provider LLM Gateway (Gemini + Groq)
- Generates bilingual plain-language warnings (English + Malayalam).
- If Gemini fails (timeout > 10s, rate limit 429, or server error 5xx), the system seamlessly switches to Groq (`llama-3.3-70b-versatile`).

### 5.4 Outbound-Only Telegram Bot Architecture
- Uses Telegram long polling (`getUpdates`).
- Zero open inbound application ports (`0.0.0.0`) on the AWS Security Group.
- Supports `/status <district>`, `/subscribe <district>`, `/unsubscribe`, `/history`, and `/disclaimer`.

---

## 6. Repository Documentation Structure

The documentation for this project is organized under the [`docs/`](file:///d:/projects/malabar_watch/docs) directory:
- [`docs/ARCHITECTURE.md`](file:///d:/projects/malabar_watch/docs/ARCHITECTURE.md) - Full technical architecture specification.
- [`docs/DATA_INGESTION_SPEC.md`](file:///d:/projects/malabar_watch/docs/DATA_INGESTION_SPEC.md) - Open-Meteo integration & calculations.
- [`docs/RISK_MODEL_SPEC.md`](file:///d:/projects/malabar_watch/docs/RISK_MODEL_SPEC.md) - Risk threshold matrix & historical event context.
- [`docs/LLM_PROMPT_ENGINEERING.md`](file:///d:/projects/malabar_watch/docs/LLM_PROMPT_ENGINEERING.md) - Gemini/Groq prompt engineering & JSON schema.
- [`docs/TELEGRAM_BOT_GUIDE.md`](file:///d:/projects/malabar_watch/docs/TELEGRAM_BOT_GUIDE.md) - Telegram bot setup, commands & BotFather guide.
- [`docs/INFRA_AND_SECURITY.md`](file:///d:/projects/malabar_watch/docs/INFRA_AND_SECURITY.md) - AWS EC2 Free Tier, SSM Session Manager, Terraform & GitHub Actions CI/CD.
- [`docs/EXTERNAL_SETUP_GUIDE.md`](file:///d:/projects/malabar_watch/docs/EXTERNAL_SETUP_GUIDE.md) - AWS account setup, IAM, SSM, and Telegram setup guide.
- [`docs/DISCLAIMER.md`](file:///d:/projects/malabar_watch/docs/DISCLAIMER.md) - Project disclaimer & safety guidelines.

