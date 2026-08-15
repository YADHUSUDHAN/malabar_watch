# Malabar Watch (മലബാർ വാച്ച്)
### AI-Powered Rainfall & Landslide Early-Warning Agent for Kerala

[![Project Status: Planning](https://img.shields.io/badge/status-planning--phase-blue)](./docs/ARCHITECTURE.md)
[![Recurring Infrastructure Cost](https://img.shields.io/badge/cost-%E2%82%B90%2Fmonth-brightgreen)](./docs/INFRA_AND_SECURITY.md)
[![Data Provider: Open--Meteo](https://img.shields.io/badge/data-Open--Meteo-orange)](./docs/DATA_INGESTION_SPEC.md)
[![LLM Primary: Gemini](https://img.shields.io/badge/LLM-Google%20Gemini-blue)](./docs/LLM_PROMPT_ENGINEERING.md)
[![LLM Fallback: Groq](https://img.shields.io/badge/Fallback-Groq%20LLaMA--3.3-purple)](./docs/LLM_PROMPT_ENGINEERING.md)
[![Cloud: GCP Always Free e2-micro](https://img.shields.io/badge/cloud-GCP%20Always%20Free-blue)](./docs/INFRA_AND_SECURITY.md)

**Malabar Watch** is a self-hosted, near-zero-cost AI early-warning agent monitoring extreme rainfall and landslide risks across vulnerable Kerala districts (Wayanad, Idukki, Kottayam). The agent evaluates cumulative rainfall metrics, reasons over historical disaster context using **Google Gemini** (with **Groq** automatic failover), and pushes plain-language **bilingual warnings (English + Malayalam)** over Telegram.

> ⚠️ **Disclaimer:** This is an educational demonstration and portfolio project. Always follow official alerts from the **India Meteorological Department (IMD)** and **Kerala State Disaster Management Authority (KSDMA)**. Read [docs/DISCLAIMER.md](docs/DISCLAIMER.md) for details.

---

## 🌟 Key Highlights

- **₹0/Month Recurring Infrastructure Cost:** Runs on GCP Compute Engine Always Free Tier (`e2-micro`, 0.25-2 vCPU, 1 GB RAM, 30 GB Persistent Disk + 2 GB Swap).
- **High-Resolution Data Ingestion:** Fetches hourly precipitation data for target micro-zones (Vythiri/Mundakkai in Wayanad, Munnar in Idukki, Teekoy in Kottayam) via **Open-Meteo API** (zero API key required).
- **Deterministic Multi-Tier Risk Engine:** Evaluates rolling 24h, 48h, 72h totals and **Antecedent Precipitation Index ($API$)** values against established thresholds (Low 🟢, Moderate 🟡, High 🟠, Severe 🔴).
- **Resilient Dual LLM Reasoning Gateway:** Uses **Google Gemini** (`gemini-2.5-flash`) as primary, automatically failing over to **Groq** (`llama-3.3-70b-versatile`) on timeouts or rate limits.
- **Bilingual Output (English + Malayalam):** Generates structured, plain-language advisories in both languages simultaneously.
- **Outbound-Only Telegram Bot:** Long-polling Telegram bot with zero public inbound ports open on the host. Supports `/status`, `/subscribe`, `/history`, and automated push warnings.
- **Infrastructure as Code & CI/CD:** Fully provisioned with Terraform and deployed via GitHub Actions using OIDC keyless authentication.

---

## 📐 System Architecture

```
 ┌─────────────────────────────┐        ┌─────────────────────────────┐
 │  Open-Meteo Weather API     │        │  Historical Disaster Store  │
 │  (Hourly rain in mm)        │        │  (Wayanad 2024, Idukki 2020)│
 └──────────────┬──────────────┘        └──────────────┬──────────────┘
                │ Outbound HTTPS                       │
                ▼                                      ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │            GCP Compute Engine Always Free (e2-micro)               │
 │                                                                    │
 │   ┌──────────────────┐               ┌─────────────────────────┐   │
 │   │ Data Collector   │──────────────▶│ SQLite Storage (WAL)    │   │
 │   └──────────────────┘               └────────────┬────────────┘   │
 │                                                   │                │
 │                                                   ▼                │
 │                                      ┌─────────────────────────┐   │
 │                                      │ Deterministic Risk Model│   │
 │                                      └────────────┬────────────┘   │
 │                                                   │                │
 │                                                   ▼                │
 │                                      ┌─────────────────────────┐   │
 │                                      │ Dual LLM Gateway        │   │
 │                                      │ (Gemini ➔ Groq Fallback)│   │
 │                                      └────────────┬────────────┘   │
 │                                                   │                │
 │                                                   ▼                │
 │                                      ┌─────────────────────────┐   │
 │                                      │ Bilingual Telegram Bot  │   │
 │                                      └────────────┬────────────┘   │
 └───────────────────────────────────────────────────┼────────────────┘
                                                     │ Outbound HTTPS
                                                     ▼
                                     ┌────────────────────────────────┐
                                     │  Telegram Messenger App        │
                                     │  (End Users / Alert Channel)   │
                                     └────────────────────────────────┘
```

---

## 📚 Master Documentation Suite

All architectural planning, tradeoff analysis, standards, and design documentation are available in the [`docs/`](docs) directory:

- [**Tradeoff Analysis & Component Selection (`docs/COMPONENT_SELECTION_TRADEOFFS.md`)**](docs/COMPONENT_SELECTION_TRADEOFFS.md): Exhaustive ADR detailing why every technology was chosen and why alternative options (OpenWeather, GPT-4o, WhatsApp, AWS/Oracle) were evaluated.
- [**Standard Practices & LLM Evals (`docs/EVALS_AND_QUALITY_ASSURANCE.md`)**](docs/EVALS_AND_QUALITY_ASSURANCE.md): 12-factor app compliance, automated LLM eval benchmarks, testing hierarchy, and observability.
- [**Master Architecture Blueprint (`docs/ARCHITECTURE.md`)**](docs/ARCHITECTURE.md): Component breakdown, database schema, end-to-end control flow.
- [**Data Ingestion Specification (`docs/DATA_INGESTION_SPEC.md`)**](docs/DATA_INGESTION_SPEC.md): Open-Meteo endpoint specs, district coordinates, Antecedent Precipitation Index formulas.
- [**Risk Model Specification (`docs/RISK_MODEL_SPEC.md`)**](docs/RISK_MODEL_SPEC.md): Threshold matrix, risk levels, and historical disaster context schemas.
- [**LLM Prompt Engineering Specification (`docs/LLM_PROMPT_ENGINEERING.md`)**](docs/LLM_PROMPT_ENGINEERING.md): Gemini + Groq failover gateway, prompts, bilingual JSON schema.
- [**Telegram Bot Guide (`docs/TELEGRAM_BOT_GUIDE.md`)**](docs/TELEGRAM_BOT_GUIDE.md): Step-by-step BotFather setup, commands list, sample output.
- [**Infrastructure & Security Specification (`docs/INFRA_AND_SECURITY.md`)**](docs/INFRA_AND_SECURITY.md): GCP Compute Engine specs, zero-inbound Bastion, Terraform, GitHub Actions OIDC pipeline.
- [**Safety Disclaimer (`docs/DISCLAIMER.md`)**](docs/DISCLAIMER.md): Educational scope and official emergency agency links.

---

## 🛠️ Technology Stack

- **Language:** Python 3.12
- **Data Source:** Open-Meteo API
- **LLMs:** Google Gemini (`gemini-2.5-flash`), Groq (`llama-3.3-70b-versatile`)
- **Database:** SQLite 3 (WAL mode)
- **Bot Engine:** `python-telegram-bot`
- **Cloud Provider:** Google Cloud Platform (Compute Engine `e2-micro` Always Free)
- **IaC:** Terraform
- **CI/CD:** GitHub Actions + OIDC
