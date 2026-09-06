# Feature Spec: Bilingual Telegram Bot Engine & Subscriber Dispatcher

- **Spec ID**: `SPEC-004`
- **Status**: Implemented
- **Owner**: Malabar Watch Engineering
- **Target Release**: `v0.1.0`
- **Dependencies**: `SPEC-001` (Data Ingestion), `SPEC-002` (Risk Engine), `SPEC-003` (Dual-LLM Gateway), `python-telegram-bot`

---

## 1. Overview & Business Intent

The primary mission of **Malabar Watch** is to deliver actionable, life-saving rainfall and landslide warnings directly to residents, responders, and local administrators across high-risk Western Ghats districts (Wayanad, Idukki, Kottayam).

While upstream specifications compute deterministic risk (`SPEC-002`) and synthesize culturally-grounded bilingual advisories (`SPEC-003`), **`SPEC-004` is the outbound delivery and user-interaction channel**. It provides:
1. **Automated Alert Dispatch**: Instant broadcast of bilingual alerts when risk levels escalate (`MODERATE`, `HIGH`, `SEVERE`).
2. **Interactive On-Demand Bot**: Responsive Telegram bot allowing users to query live risk status, inspect historical rainfall trends, and manage district alert subscriptions.
3. **Zero-Inbound Security Architecture**: Implements outbound-only HTTP long-polling (`getUpdates`), requiring **zero open inbound network ports** on host machines or cloud VMs.

---

## 2. Architecture & Security Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Malabar Watch Host / VM                           │
│                                                                             │
│  ┌──────────────────────┐    Outbound HTTPS Polling    ┌─────────────────┐  │
│  │   Telegram Bot App   │ ───────────────────────────> │  Telegram API   │  │
│  │ (python-telegram-bot)│ <─────────────────────────── │  (getUpdates)   │  │
│  └──────────┬───────────┘       (No Inbound Ports)     └────────┬────────┘  │
│             │                                                   │           │
│             ├───────────────┐                                   │           │
│             ▼               ▼                                   │           │
│  ┌────────────────────┐ ┌────────────────────┐                  │           │
│  │ Command Handlers   │ │  Alert Dispatcher  │                  ▼           │
│  │ /start, /status,   │ │ (Broadcast pushes) │         ┌─────────────────┐  │
│  │ /subscribe, etc.   │ └─────────┬──────────┘         │ Telegram User / │  │
│  └──────────┬─────────┘           │                    │ Subscriber Chat │  │
│             │                     │                    └─────────────────┘  │
│             ▼                     ▼                                         │
│  ┌───────────────────────────────────────────┐                              │
│  │       SQLite Storage Layer (WAL Mode)     │                              │
│  │  - subscribers: chat_id, district, active │                              │
│  │  - alert_logs: delivery audit trail       │                              │
│  └───────────────────────────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Security & Operational Principles
- **Zero Inbound Ports (`0.0.0.0`)**: Unlike webhook bots that require public IPs, open ports (80/443), and TLS certificates, this bot runs exclusively via outbound HTTP long-polling. This is firewall-safe, NAT-safe, and aligns with AWS Free Tier EC2 deployment via AWS SSM.
- **Graceful Error Handling**: Handles Telegram rate limits (`RetryAfter`), chat migrations, and deactivates users who block the bot (`Forbidden`).
- **Dry-Run & Mocking Support**: All bot formatting and dispatch pathways can execute without an active Telegram bot token in development and CI environments.

---

## 3. Bot Commands & Interaction Workflows

| Command | Usage | Description |
| :--- | :--- | :--- |
| `/start` | `/start` | Welcome message, safety disclaimer, and interactive inline buttons for quick district selection. |
| `/status [district]` | `/status wayanad`, `/status idukki`, `/status kottayam` | On-demand live weather metrics, risk evaluation, and synthesized bilingual advisory. If district is omitted, shows inline keyboard. |
| `/subscribe [district]` | `/subscribe wayanad` or `/subscribe all` | Subscribes chat to automated push alerts for a specific district or all micro-zones. |
| `/unsubscribe` | `/unsubscribe` | Opts out of automated push alerts. |
| `/history [district]` | `/history wayanad` | Displays 24h, 48h, 72h rainfall totals and antecedent moisture trends. |
| `/disclaimer` | `/disclaimer` | Displays project scope, non-governmental educational status, and official emergency contacts (KSDMA, NDRF). |
| `/help` | `/help` | Detailed command list and usage guidance. |

### Interactive Menus (Inline Keyboards)
When users trigger `/start` or `/status` without parameters, the bot presents inline keyboard buttons:
- `📍 Wayanad (വയനാട്)` ➔ `district:wayanad`
- `📍 Idukki (ഇടുക്കി)` ➔ `district:idukki`
- `📍 Kottayam (കോട്ടയം)` ➔ `district:kottayam`
- `🌐 All Districts (എല്ലാ ജില്ലകളും)` ➔ `district:all`

---

## 4. Message Formatting Specification

Alerts and status cards are formatted in strict **Telegram HTML** (avoiding Markdown reserved-character escaping bugs).

### Standard Alert Template Structure
```html
🚨 <b>MALABAR WATCH | മലബാർ വാച്ച് മുന്നറിയിപ്പ്</b>
───────────────────────────
📍 <b>മേഖല / Region:</b> Wayanad (വയനാട് - വൈത്തിരി / മേപ്പാടി)
⚠️ <b>അപകട സാധ്യത / Risk Level:</b> 🔴 <b>SEVERE ALERT (റെഡ് അലർട്ട്)</b>
⏱️ <i>2026-09-06 16:30 IST</i>

🌧️ <b>മഴ കണക്കുകൾ / Rainfall Metrics:</b>
 • 1 മണിക്കൂർ (1h): <b>28.0 mm</b>
 • 24 മണിക്കൂർ (24h): <b>215.0 mm</b>
 • 48 മണിക്കൂർ (48h): <b>310.0 mm</b>
 • മണ്ണിലെ ജലാംശം (API Index): <b>158.0</b> (Critical Saturation)

───────────────────────────
<b>English Advisory (ഇംഗ്ലീഷ്):</b>
Wayanad is experiencing severe conditions with 28 mm rain in the past hour and 215 mm in the last 24 hours. A red alert is issued due to high risk of landslides and debris flows.
👉 <i>Action: Stay away from riverbanks and steep slopes; move immediately to designated safe shelters.</i>

───────────────────────────
<b>മലയാളം നിർദ്ദേശം:</b>
വയനാട് ജില്ലയിൽ കഴിഞ്ഞ 24 മണിക്കൂറിൽ 215 മിമി അതിതീവ്ര മഴ രേഖപ്പെടുത്തി. മണ്ണിലെ ജലാംശം അതീവ ഗുരുതര നിലയിലാണ്. ഉരുൾപൊട്ടൽ, മലവെള്ളപ്പാച്ചിൽ സാധ്യത നിലനിൽക്കുന്നു.
👉 <i>നിർദ്ദേശം: മലയോര മേഖലകളിലുള്ളവർ സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക. അധികാരികളുടെ നിർദ്ദേശങ്ങൾ കർശനമായി പാലിക്കുക.</i>

───────────────────────────
📜 <b>ചരിത്രപരമായ പശ്ചാത്തലം / Historical Context:</b>
⚠️ <i>Conditions mirror the July 2024 Chooralmala disaster rainfall patterns.</i>
───────────────────────────
⚠️ <i>Malabar Watch is an AI experimental project. In emergencies, strictly follow IMD & KSDMA directives (Toll-free: 1077 / 1070).</i>
```

---

## 5. Subscriber Storage Schema

In `src/malabar_watch/storage/`:

```sql
-- Subscribers table
CREATE TABLE IF NOT EXISTS subscribers (
    chat_id INTEGER PRIMARY KEY,
    district_id TEXT NOT NULL DEFAULT 'all',
    is_active INTEGER NOT NULL DEFAULT 1,
    subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alert delivery audit log
CREATE TABLE IF NOT EXISTS alert_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district_id TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    assessment_id INTEGER,
    dispatched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    delivered_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0
);
```

---

## 6. End-to-End Autonomous Pipeline Flow

In addition to user-initiated queries, the system supports a unified hourly pipeline run:
1. **Data Ingestion (`SPEC-001`)**: Polls Open-Meteo for all micro-zones.
2. **Deterministic Risk Evaluation (`SPEC-002`)**: Evaluates $R_{24\text{h}}$, $API$, and state transitions (`ESCALATED`, `SUSTAINED`, `DOWNGRADED`).
3. **Dual-LLM Advisory Synthesis (`SPEC-003`)**: If `requires_alert=True`, synthesizes bilingual warning.
4. **Subscriber Dispatch (`SPEC-004`)**:
   - Queries all active subscribers matching `district_id` or `all`.
   - Formats HTML alert.
   - Dispatches via Telegram Bot API with rate-limiting.
   - Logs broadcast metrics into `alert_logs`.

---

## 7. Acceptance Criteria & Test Strategy

- [x] **AC-1 (Zero Inbound Ports)**: Telegram bot initializes and executes via long-polling (`Application.run_polling()`), binding to no local network ports.
- [x] **AC-2 (Command Handlers)**: `/start`, `/status`, `/subscribe`, `/unsubscribe`, `/history`, `/disclaimer`, `/help` execute correctly with bilingual responses.
- [x] **AC-3 (Inline Keyboards)**: Interactive district selection buttons trigger callback queries and return targeted district status.
- [x] **AC-4 (Subscriber Persistence)**: Subscribe and unsubscribe commands correctly update SQLite database records.
- [x] **AC-5 (Alert Formatting)**: Generated alert messages conform to Telegram HTML with correct emoji indicators, metrics, and bilingual sections.
- [x] **AC-6 (Resilient Dispatcher)**: Broadcast engine handles blocked chats (`Forbidden`), logs delivery count in `alert_logs`, and does not crash on API exceptions.
- [x] **AC-7 (CLI Integration)**: `malabar-watch --test-bot` tests mock message generation, and `malabar-watch --bot` starts the live bot daemon.
