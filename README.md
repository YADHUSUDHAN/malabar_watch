# Malabar Watch (മലബാർ വാച്ച്)
### AI-Powered Rainfall & Landslide Early-Warning Agent for Kerala

[![Live Bot](https://img.shields.io/badge/Telegram-@mapabar_watch_alert_bot-2CA5E0?logo=telegram&logoColor=white)](https://t.me/mapabar_watch_alert_bot)
[![Project Status: Production Ready](https://img.shields.io/badge/status-production--ready-brightgreen)](./docs/ARCHITECTURE.md)
[![Tests: 82 Passed](https://img.shields.io/badge/tests-82%20passed-brightgreen)](./tests)
[![IaC: Terraform](https://img.shields.io/badge/IaC-Terraform-blueviolet)](./terraform)
[![Deployment Guide](https://img.shields.io/badge/guide-AWS%20Zero--Trust%20Deployment-blue)](./docs/AWS_TERRAFORM_BEGINNER_GUIDE.md)
[![Cost](https://img.shields.io/badge/cost-%E2%82%B90%2Fmonth-brightgreen)](./docs/INFRA_AND_SECURITY.md)
[![LLM: Gemini + Groq](https://img.shields.io/badge/LLM-Gemini%20%2B%20Groq%20Failover-purple)](./docs/LLM_PROMPT_ENGINEERING.md)

**Malabar Watch** is an autonomous, self-hosted AI early-warning agent monitoring extreme rainfall and landslide risks across vulnerable Kerala highland districts (Wayanad, Idukki, Kottayam). The agent continuously evaluates cumulative rainfall metrics, reasons over historical disaster context using a resilient **Dual-LLM Gateway** (**Google Gemini** primary with **Groq LLaMA** fallback), and dispatches structured, plain-language **bilingual warnings (English + Malayalam)** over Telegram.

> 🤖 **Try the Live Bot on Telegram:** [@mapabar_watch_alert_bot](https://t.me/mapabar_watch_alert_bot)  
> Send `/status` to query live telemetry & geotechnical risk assessments for Kerala highland districts.
>
> ⚠️ **Disclaimer:** This is an educational demonstration and portfolio project. In real emergencies, always follow official directives from the **India Meteorological Department (IMD)** and **Kerala State Disaster Management Authority (KSDMA)**. Read [docs/DISCLAIMER.md](docs/DISCLAIMER.md) for details.

---

## 🌟 Key Highlights

- **Live 24/7 Cloud Deployment:** Provisioned on AWS EC2 Free Tier (`t3.micro` in Mumbai `ap-south-1`) via **Terraform** for **₹0/month**.
- **Resilient Dual LLM Reasoning Gateway:** Uses **Google Gemini** as primary, automatically failing over to **Groq** on rate limits/timeouts, with a deterministic template fallback ensuring zero downtime.
- **Geotechnical Risk Grounding:** Evaluates rolling 24h, 48h, 72h totals and **Antecedent Precipitation Index ($API$)** to model soil saturation deterministically (no hallucinated risk math).
- **Historical Analog Context:** Matches current conditions against landmark disaster benchmarks (2024 Chooralmala/Mundakkai, 2020 Pettimudi, 2021 Koottickal).
- **Bilingual Output (English + Malayalam):** Generates structured, plain-language advisories in both languages simultaneously.
- **Zero Inbound Ports Security:** Host operates with zero public inbound ports (`0.0.0.0/0` blocked; no SSH port 22). Managed keylessly via **AWS Systems Manager (SSM) Session Manager**.
- **Linux systemd Daemons & Timers:** Outbound long-polling bot daemon auto-restarts on failure; hourly timer executes autonomous ingestion cycles.
- **Production Engineering Standards:** 82 passing tests, static typing (`mypy`), linting (`ruff`), and centralized rotating file logging.

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
- [**Beginner's Guide to AWS & Terraform (`docs/AWS_TERRAFORM_BEGINNER_GUIDE.md`)**](docs/AWS_TERRAFORM_BEGINNER_GUIDE.md): Plain-English AWS, Terraform, and Zero-Inbound deployment walkthrough.
- [**Safety Disclaimer (`docs/DISCLAIMER.md`)**](docs/DISCLAIMER.md): Educational scope and official emergency agency links.

### 📋 Feature Specifications (Spec-Driven Development)
- [**SPEC-001: Data Ingestion Engine**](specs/001_DATA_INGESTION.md): Hourly Open-Meteo precipitation ingestion, derived rolling sums (1h, 24h, 48h, 72h), and Antecedent Precipitation Index ($API$).
- [**SPEC-002: Geotechnical Risk Engine**](specs/002_RISK_ENGINE.md): Deterministic multi-tier risk matrix, geotechnical precedent rules, and historical disaster matching.
- [**SPEC-003: Resilient Dual-LLM Gateway**](specs/003_LLM_GATEWAY.md): Google Gemini primary $\to$ Groq LLaMA fallback $\to$ Deterministic template failover with bilingual synthesis.
- [**SPEC-004: Telegram Early-Warning Bot**](specs/004_TELEGRAM_BOT.md): Long-polling outbound daemon, interactive menus, and subscriber alert dispatcher.
- [**SPEC-005: Cloud Deployment & Monitoring**](specs/005_CLOUD_DEPLOYMENT.md): AWS Free Tier `t3.micro` provisioning with Terraform, 2 GB Swap, Zero-Inbound SSM security, and `systemd` automation.

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

