# Architecture Tradeoff Analysis & Component Selection Rationale

This document provides a comprehensive Architectural Decision Record (ADR) detailing **why every technology and component was selected** for **Malabar Watch**, alongside a detailed comparison of **rejected alternative options** and the specific reasons for their rejection.

---

## 1. Summary Matrix of Architectural Choices

| Architectural Dimension | Selected Choice | Rejected Alternatives | Primary Selection Driver |
|---|---|---|---|
| **Architecture Pattern** | Hybrid Deterministic Scorer + LLM | Pure LLM End-to-End, ML Classification Model | Zero LLM hallucination risk on threshold math; immediate explainability. |
| **Weather Data Source** | Open-Meteo API | OpenWeatherMap, IMD Data Portal, WeatherAPI, Tomorrow.io | Free, no API key required, high-resolution hourly precipitation data. |
| **Primary LLM** | Google Gemini (`gemini-2.5-flash`) | OpenAI GPT-4o-mini, Anthropic Claude 3.5 Haiku, DeepSeek V3 | Generous free tier (15 RPM / 1M TPM), superior native Malayalam generation. |
| **Fallback LLM** | Groq API (`llama-3.3-70b-versatile`) | Together AI, Ollama Local, Cerbras AI | Ultra-fast inferencing (<500ms), generous free tier (30 RPM / 14.4k RPD). |
| **Alert Delivery Channel** | Telegram Bot API | WhatsApp Business API, SMS (Twilio), Mobile App (Flutter), Web Dashboard | Outbound-only long polling (zero open ports), 100% free unlimited push alerts. |
| **Cloud Compute Host** | AWS EC2 Free Tier (`t2.micro` / `t3.micro`) | GCP Compute Engine, Oracle Cloud Free Tier, Azure B1s, Render/Fly.io | Low network latency (`ap-south-1` Mumbai), 750 free hours/mo, seamless AWS Systems Manager integration. |
| **Database Engine** | SQLite 3 (WAL Mode) | PostgreSQL / MySQL, MongoDB, Redis, Cloud DynamoDB | Zero ops, zero RAM overhead, embedded local file storage with high concurrency. |
| **Infrastructure as Code** | Terraform (`hashicorp/aws`) | AWS CloudFormation, Pulumi, Manual Cloud Console | Vendor-neutral industry standard, declarative state management. |
| **Security Access Model** | AWS Security Groups + SSM Session Manager | Open Public SSH (Port 22), OpenVPN Server, Tailscale / Cloudflare Tunnel | True zero public exposed inbound application ports; keyless IAM-authenticated administration. |
| **Deployment & CI/CD** | GitHub Actions + AWS OIDC | Jenkins, GitLab CI, Manual SSH deployment | Free for public repos, keyless OIDC authentication eliminates long-lived credentials. |

---

## 2. Exhaustive Deep-Dive per Component

### 2.1 Architecture Pattern: Hybrid Scorer + LLM vs. Alternatives

- **SELECTED:** **Hybrid Deterministic Scorer + LLM Summarizer**
  - *Why Chosen:* Risk thresholds (e.g. 100mm / 24h = High Risk) must be 100% deterministic and auditable. Python code handles exact numerical comparison. The LLM is strictly tasked with natural language translation, empathy, and contextual synthesis.
- **REJECTED ALTERNATIVES:**
  - ❌ **Pure LLM End-to-End Reasoning (Raw Data ➔ LLM ➔ Alert):**
    - *Reason for Rejection:* High risk of LLM hallucinations in numerical logic (e.g. LLM misinterpreting 180mm as "low" or failing to sum multi-day arrays reliably). Unacceptable risk for safety-oriented software.
  - ❌ **Supervised Machine Learning Model (Random Forest / XGBoost / PyTorch):**
    - *Reason for Rejection:* Overkill for MVP; requires massive labeled historical geotechnical datasets (soil moisture, slope angle, friction coefficients) which are not publicly aggregated in real-time. Can be introduced in Phase 2.

---

### 2.2 Weather Data Source: Open-Meteo API vs. Alternatives

- **SELECTED:** **Open-Meteo API**
  - *Why Chosen:*
    1. **100% Free with No API Key:** Eliminates key management friction and risk of API key depletion during public demos.
    2. **High-Resolution Hourly Precipitation Data:** Provides exact past and forecast hourly rain in mm derived from ECMWF and GFS global models.
    3. **Precise Coordinate Querying:** Accepts exact latitude/longitude coordinates (e.g. `11.6084° N` for Wayanad slope).
- **REJECTED ALTERNATIVES:**
  - ❌ **OpenWeatherMap Free Tier:**
    - *Reason for Rejection:* Free tier requires API key setup, limits historical hourly data access (One Call API 3.0 requires credit card activation), and caps daily calls.
  - ❌ **IMD (India Meteorological Department) Open Data Portal:**
    - *Reason for Rejection:* Lacks a reliable, standardized JSON REST API. Data is often published as static PDF bulletins or web scrapes with inconsistent uptime and high latency.
  - ❌ **WeatherAPI / Tomorrow.io:**
    - *Reason for Rejection:* Strict trial expiration (14 days) or low monthly request caps on free tiers requiring paid credit cards.

---

### 2.3 Primary LLM Provider: Google Gemini API vs. Alternatives

- **SELECTED:** **Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`)**
  - *Why Chosen:*
    1. **Exceptional Free Tier:** 15 Requests Per Minute (RPM), 1,000,000 Tokens Per Minute (TPM), 1,500 Requests Per Day (RPD)—far exceeding our hourly needs.
    2. **Superior Malayalam Language Generation:** Trained extensively on multilingual corpora; produces natural, grammatically sound Malayalam disaster advisories without awkward translation artifacts.
    3. **Native JSON Schema Enforcement:** Supports `response_mime_type: "application/json"` with strict schema validation.
- **REJECTED ALTERNATIVES:**
  - ❌ **OpenAI GPT-4o / GPT-4o-mini:**
    - *Reason for Rejection:* Requires pre-funded API balance (no true free tier API credits for ongoing autonomous agents).
  - ❌ **Anthropic Claude 3.5 Haiku:**
    - *Reason for Rejection:* Requires paid API credits with deposit limits; no perpetual free tier API access.
  - ❌ **DeepSeek API (DeepSeek-V3 / R1):**
    - *Reason for Rejection:* Outstanding performance, but hosted API service occasionally experiences high concurrency rate limits (429) during peak global traffic. Used as secondary inspiration.

---

### 2.4 Fallback LLM Provider: Groq API vs. Alternatives

- **SELECTED:** **Groq API (`llama-3.3-70b-versatile`)**
  - *Why Chosen:*
    1. **Sub-Second Speed:** Ultra-fast LPUs (Language Processing Units) generate responses in <500ms, ensuring immediate failover if Gemini stalls.
    2. **Generous Free Tier:** 30 RPM, 14,400 RPD on `llama-3.3-70b-versatile`.
    3. **Seamless Provider Interface:** Compatible with standard OpenAI JSON client requests.
- **REJECTED ALTERNATIVES:**
  - ❌ **Self-Hosted Local LLM (Ollama / Llama.cpp on Cloud VM):**
    - *Reason for Rejection:* Running a 7B/70B model locally requires heavy GPU instances (expensive) or causes high CPU latency (30+ seconds per response) on CPU VMs, consuming storage and RAM.
  - ❌ **Together AI / Replicate:**
    - *Reason for Rejection:* Requires credit card balance after initial small trial credits expire.

---

### 2.5 Alert Channel: Telegram Bot API vs. Alternatives

- **SELECTED:** **Telegram Bot API (Long Polling)**
  - *Why Chosen:*
    1. **Zero Open Inbound Ports:** Supports `getUpdates` outbound long polling. The VM never needs to expose an HTTP port (`80`/`443`) or maintain public SSL certificates.
    2. **100% Free Unlimited Messaging:** No per-message fees for automated push notifications to channels or group chats.
    3. **Rich Formatting & Interactive UI:** Native support for HTML styling, inline keyboards, custom bot commands, and push notifications.
- **REJECTED ALTERNATIVES:**
  - ❌ **WhatsApp Business API:**
    - *Reason for Rejection:* Extremely expensive per-message template costs, complex Meta business verification, and strict template approval requirements for alerts.
  - ❌ **SMS Services (Twilio / Fast2SMS):**
    - *Reason for Rejection:* High per-SMS charges (~₹0.25 - ₹0.50 per SMS), strictly violating the ₹0 recurring cost constraint.
  - ❌ **Custom Mobile App (Flutter / React Native):**
    - *Reason for Rejection:* Requires Apple Developer Account ($99/year) and Google Play Console ($25), push notification server infrastructure (FCM), and complex mobile app maintenance.

---

### 2.6 Cloud Compute Host: AWS EC2 Free Tier vs. Alternatives

- **SELECTED:** **Amazon Web Services (AWS) EC2 (`t2.micro` / `t3.micro`) & Local-First Verification Workflow**
  - *Why Chosen:*
    1. **Local-First Verification Strategy:** The complete system is verified end-to-end locally before any cloud infrastructure is provisioned, minimizing unexpected cloud compute issues or stray billing.
    2. **Low-Latency Indian Infrastructure:** AWS `ap-south-1` (Mumbai) offers sub-30ms round-trip latency to Kerala ISP networks and Telegram datacenters.
    3. **AWS Systems Manager (SSM) Integration:** Clean, keyless terminal access without exposing SSH port 22 or managing static SSH keys.
    4. **Generous Free Tier & Predictable Transition:** 750 free hours/month on EC2 Free Tier; seamless migration to low-cost AWS Lightsail ($3.50/month) or spot instances if needed.
- **REJECTED ALTERNATIVES:**
  - ❌ **Oracle Cloud Free Tier (ARM Ampere A1):**
    - *Reason for Rejection:* High signup verification failure rates, aggressive card rejections, and frequent out-of-capacity errors for ARM shapes in India regions.
  - ❌ **GCP Compute Engine Always Free (e2-micro):**
    - *Reason for Rejection:* Always Free tier is restricted to US regions (`us-central1`, `us-east1`, `us-west1`), resulting in higher latency (~220ms) from Kerala compared to AWS Mumbai (`ap-south-1`).
  - ❌ **Serverless PaaS (Render / Fly.io / Vercel):**
    - *Reason for Rejection:* Free tiers put background workers to sleep after inactivity, breaking hourly cron schedules or requiring inbound pingers (which expose ports).

---

### 2.7 Storage Engine: SQLite 3 (WAL Mode) vs. Alternatives

- **SELECTED:** **SQLite 3 (with Write-Ahead Logging enabled)**
  - *Why Chosen:*
    1. **Zero Resource Overhead:** Operates inside the Python process without running a background daemon (saving RAM and CPU).
    2. **High Reliability & ACID:** WAL mode allows concurrent readers while writing, handling thousands of hourly logs easily.
    3. **Single File Backup:** Easy file copy for snapshot backups and local developer debugging.
- **REJECTED ALTERNATIVES:**
  - ❌ **PostgreSQL / MySQL Daemon:**
    - *Reason for Rejection:* Consumes 150-300 MB of continuous background RAM, requires database user setup, password rotation, and ongoing maintenance.
  - ❌ **MongoDB / NoSQL:**
    - *Reason for Rejection:* Unnecessary memory overhead and complexity for structured tabular metrics.

---

### 2.8 Security Model: AWS Security Groups & SSM Session Manager vs. Alternatives

- **SELECTED:** **AWS Security Groups & AWS SSM Session Manager (Zero Inbound App Ports)**
  - *Why Chosen:*
    1. **Zero Public Inbound Exposure:** Security Groups block 100% of incoming traffic from the internet (`0.0.0.0/0`).
    2. **Keyless Session Manager:** Terminal access and code deployment utilize AWS SSM Session Manager backed by IAM policies, eliminating SSH port 22 and leaked private keys.
    3. **Outbound-Only Communication:** Telegram long-polling and Open-Meteo polling originate strictly outbound over HTTPS.
- **REJECTED ALTERNATIVES:**
  - ❌ **Public Webhook Servers (Port 80/443 Open to 0.0.0.0/0):**
    - *Reason for Rejection:* Exposes host to web vulnerabilities, requires managing SSL certificates (Certbot), and opens inbound attack vectors.
  - ❌ **Self-Hosted VPN (OpenVPN / WireGuard):**
    - *Reason for Rejection:* Requires opening a UDP/TCP inbound port on the VM, increasing attack surface and maintenance burden.

