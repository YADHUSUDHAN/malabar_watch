# Malabar Watch (മലബാർ വാച്ച്)
### AI-Powered Rainfall & Landslide Early-Warning Agent for Kerala

[![Project Status: Production Ready](https://img.shields.io/badge/status-production--ready-brightgreen)](./docs/ARCHITECTURE.md)
[![Tests: 82 Passed](https://img.shields.io/badge/tests-82%20passed-brightgreen)](./tests)
[![IaC: Terraform](https://img.shields.io/badge/IaC-Terraform-blueviolet)](./terraform)
[![Deployment Guide](https://img.shields.io/badge/guide-AWS%20Zero--Trust%20Deployment-blue)](./docs/AWS_TERRAFORM_BEGINNER_GUIDE.md)
[![Cost](https://img.shields.io/badge/cost-%E2%82%B90%2Fmonth-brightgreen)](./docs/INFRA_AND_SECURITY.md)
[![LLM: Gemini + Groq](https://img.shields.io/badge/LLM-Gemini%20%2B%20Groq%20Failover-purple)](./docs/LLM_PROMPT_ENGINEERING.md)

**Malabar Watch** is a self-hosted, near-zero-cost AI early-warning agent monitoring extreme rainfall and landslide risks across vulnerable Kerala districts (Wayanad, Idukki, Kottayam). The agent evaluates cumulative rainfall metrics, reasons over historical disaster context using **Google Gemini** (with **Groq** automatic failover), and pushes plain-language **bilingual warnings (English + Malayalam)** over Telegram.

> ⚠️ **Disclaimer:** This is an educational demonstration and portfolio project. Always follow official alerts from the **India Meteorological Department (IMD)** and **Kerala State Disaster Management Authority (KSDMA)**. Read [docs/DISCLAIMER.md](docs/DISCLAIMER.md) for details.

---

## 🌟 Key Highlights

- **Local-First Verification Workflow:** 100% of pipeline functions, ingestion mocks/live calls, risk scoring, bilingual LLM synthesis, and Telegram long polling are developed and verified locally before cloud deployment.
- **₹0/Month Cloud Infrastructure:** Runs on AWS EC2 Free Tier (`t2.micro` / `t3.micro`, 1 vCPU, 1 GB RAM, 30 GB EBS gp3 volume + 2 GB Linux Swap in `ap-south-1` Mumbai).
- **High-Resolution Data Ingestion:** Fetches hourly precipitation data for target micro-zones (Vythiri/Mundakkai in Wayanad, Munnar in Idukki, Teekoy in Kottayam) via **Open-Meteo API** (zero API key required).
- **Deterministic Multi-Tier Risk Engine:** Evaluates rolling 24h, 48h, 72h totals and **Antecedent Precipitation Index ($API$)** values against established thresholds (Low 🟢, Moderate 🟡, High 🟠, Severe 🔴).
- **Resilient Dual LLM Reasoning Gateway:** Uses **Google Gemini** (`gemini-2.5-flash`) as primary, automatically failing over to **Groq** (`llama-3.3-70b-versatile`) on timeouts or rate limits.
- **Bilingual Output (English + Malayalam):** Generates structured, plain-language advisories in both languages simultaneously.
- **Outbound-Only Telegram Bot:** Long-polling Telegram bot with zero public inbound ports open on the host. Supports `/status`, `/subscribe`, `/history`, and automated push warnings.
- **Keyless AWS Systems Manager (SSM) Security:** True zero inbound application ports; remote administration managed through AWS SSM without exposing public SSH (port 22).
- **Infrastructure as Code & CI/CD:** Fully provisioned with Terraform (`hashicorp/aws`) and deployed via GitHub Actions using AWS OIDC keyless authentication.

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
 │         AWS EC2 Free Tier (t2.micro/t3.micro - ap-south-1)         │
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

## 🚀 Local Run & Verification (Stage 1)

Before cloud deployment, verify the entire agent pipeline locally:

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Run test suite, linter, and static type checker
uv run pytest
uv run ruff check .
uv run mypy src

# 3. Launch CLI dry-run
uv run malabar-watch
```

---

## 📚 Master Documentation Suite

All architectural planning, tradeoff analysis, standards, and design documentation are available in the [`docs/`](docs) directory:

- [**Solution Architecture Blueprint (`Malabar-Watch-Solution-Architecture.md`)**](Malabar-Watch-Solution-Architecture.md): Master solution architecture and two-stage lifecycle specification.
- [**Tradeoff Analysis & Component Selection (`docs/COMPONENT_SELECTION_TRADEOFFS.md`)**](docs/COMPONENT_SELECTION_TRADEOFFS.md): Exhaustive ADR detailing why every technology was chosen and why alternative options were evaluated.
- [**Standard Practices & LLM Evals (`docs/EVALS_AND_QUALITY_ASSURANCE.md`)**](docs/EVALS_AND_QUALITY_ASSURANCE.md): 12-factor app compliance, automated LLM eval benchmarks, testing hierarchy, and observability.
- [**Master Architecture Blueprint (`docs/ARCHITECTURE.md`)**](docs/ARCHITECTURE.md): Component breakdown, database schema, end-to-end control flow.
- [**Data Ingestion Specification (`docs/DATA_INGESTION_SPEC.md`)**](docs/DATA_INGESTION_SPEC.md): Open-Meteo endpoint specs, district coordinates, Antecedent Precipitation Index formulas.
- [**Risk Model Specification (`docs/RISK_MODEL_SPEC.md`)**](docs/RISK_MODEL_SPEC.md): Threshold matrix, risk levels, and historical disaster context schemas.
- [**LLM Prompt Engineering Specification (`docs/LLM_PROMPT_ENGINEERING.md`)**](docs/LLM_PROMPT_ENGINEERING.md): Gemini + Groq failover gateway, prompts, bilingual JSON schema.
- [**Telegram Bot Guide (`docs/TELEGRAM_BOT_GUIDE.md`)**](docs/TELEGRAM_BOT_GUIDE.md): Step-by-step BotFather setup, commands list, sample output.
- [**Infrastructure & Security Specification (`docs/INFRA_AND_SECURITY.md`)**](docs/INFRA_AND_SECURITY.md): AWS EC2 Free Tier specs, SSM Session Manager, Terraform, GitHub Actions OIDC pipeline.
- [**External Setup Guide (`docs/EXTERNAL_SETUP_GUIDE.md`)**](docs/EXTERNAL_SETUP_GUIDE.md): Step-by-step external setup for AWS, Gemini, Groq, and Telegram.
- [**Safety Disclaimer (`docs/DISCLAIMER.md`)**](docs/DISCLAIMER.md): Educational scope and official emergency agency links.

---

## 🛠️ Technology Stack

- **Language:** Python 3.12 / 3.13
- **Data Source:** Open-Meteo API
- **LLMs:** Google Gemini (`gemini-2.5-flash`), Groq (`llama-3.3-70b-versatile`)
- **Database:** SQLite 3 (WAL mode)
- **Bot Engine:** `python-telegram-bot`
- **Cloud Provider:** Amazon Web Services (AWS EC2 `t2.micro` / `t3.micro` Free Tier in `ap-south-1`)
- **Remote Access:** AWS Systems Manager (SSM) Session Manager (Keyless)
- **IaC:** Terraform (`hashicorp/aws`)
- **CI/CD:** GitHub Actions + AWS OIDC

