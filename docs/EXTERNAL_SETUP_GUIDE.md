# External Services & Infrastructure Setup Guide

This document provides complete, step-by-step instructions for provisioning all required external services, obtaining API credentials, creating Telegram alert bots, configuring zero-cost cloud hosting on Google Cloud Platform (GCP) Compute Engine Always Free Tier, and setting up GitHub Actions secrets for **Malabar Watch (മലബാർ വാച്ച്)**.

---

## 📋 Summary of Required External Credentials

| Service | Purpose | Key / Secret Name | Cost |
| :--- | :--- | :--- | :--- |
| **Google AI Studio** | Primary LLM Reasoning Gateway | `GEMINI_API_KEY` | Free Tier available |
| **Groq Cloud** | Failover LLM Gateway | `GROQ_API_KEY` | Free Tier available |
| **Telegram BotFather** | Outbound Alert Dispatcher | `TELEGRAM_BOT_TOKEN` | Free |
| **Telegram Channel / User** | Target Alert Recipient | `TELEGRAM_CHAT_ID` | Free |
| **Open-Meteo API** | Weather & Rainfall Data Source | *None (No Key Needed)* | Free / Open Access |
| **GCP Compute Engine** | Always Free `e2-micro` Linux VM | Host IP + SSH Private Key | ₹0/month (Always Free) |
| **GitHub Repository** | Secrets & CI/CD Pipeline | Secrets configured in GitHub | Free |

---

## 1. 🤖 Google Gemini API Setup (Primary LLM)

Google Gemini (`gemini-2.5-flash`) is the primary reasoning engine responsible for digesting risk assessment metrics and generating bilingual advisories in Malayalam and English.

### Step-by-Step Guide:
1. Navigate to **[Google AI Studio](https://aistudio.google.com/)**.
2. Sign in with your Google account.
3. Click on **Get API Key** in the top navigation or side menu.
4. Click **Create API Key** (choose an existing Google Cloud project or select *Create API Key in new project*).
5. Copy the generated API key string (starts with `AIzaSy...`).
6. Store this key securely. You will set it in your local `.env` file as:
   ```ini
   GEMINI_API_KEY="AIzaSyYourGeneratedGeminiKeyHere"
   ```

---

## 2. ⚡ Groq Cloud API Setup (Fallback LLM)

Groq (`llama-3.3-70b-versatile`) acts as an instant, ultra-fast failover LLM if Gemini encounters rate limits (HTTP 429), timeouts, or API outages.

### Step-by-Step Guide:
1. Navigate to **[Groq Console](https://console.groq.com/)**.
2. Create an account or sign in.
3. In the left navigation sidebar, click **API Keys**.
4. Click **Create API Key**.
5. Give your key a name (e.g., `malabar-watch-fallback`).
6. Copy the generated key (starts with `gsk_...`).
7. Store this key securely. You will set it in your local `.env` file as:
   ```ini
   GROQ_API_KEY="gsk_YourGeneratedGroqKeyHere"
   ```

---

## 3. 📢 Telegram Bot & Channel Setup

The bot dispatches real-time weather and landslide risk advisories. It operates in **outbound-only** mode (long-polling), requiring no open inbound ports on your server.

### Step 3.1: Create Telegram Bot via BotFather
1. Open Telegram and search for `@BotFather` (verified account with a blue checkmark).
2. Start a chat and send the command:
   ```text
   /newbot
   ```
3. Enter a friendly display name for your bot, e.g.:
   `Malabar Watch Alert Agent`
4. Enter a unique username ending in `bot`, e.g.:
   `malabar_watch_alert_bot`
5. BotFather will reply with your **HTTP API Token** (e.g., `7890123456:AAFd...`).
6. Save this token as `TELEGRAM_BOT_TOKEN`.

### Step 3.2: Create Channel or Group & Get Chat ID
1. Create a new Telegram **Channel** or **Group** (e.g., `Malabar Early Warnings`).
2. Add your newly created bot (`@malabar_watch_alert_bot`) as an **Administrator** in the channel with **Post Messages** permission.
3. Send a test message in the channel (e.g., `Malabar Watch initialized`).
4. Retrieve your `TELEGRAM_CHAT_ID`:
   - **Option A (Browser)**: Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in your browser. Look for `"chat":{"id": -100xxxxxxxxxx}` in the JSON response.
   - **Option B (Bot helper)**: Add `@GetIDsBot` to your channel or forward a message from your channel to `@GetIDsBot`.
5. Note: Channel IDs in Telegram typically start with `-100` (e.g., `-1001234567890`).
6. Save this ID in your local `.env` file as:
   ```ini
   TELEGRAM_BOT_TOKEN="7890123456:AAFdYourTelegramTokenHere"
   TELEGRAM_CHAT_ID="-1001234567890"
   ```

---

## 4. 🌧️ Open-Meteo Weather API Setup

Open-Meteo provides high-resolution hourly precipitation data for target districts in Kerala without requiring any API key or subscription.

### Key API Details:
- **Base Endpoint**: `https://api.open-meteo.com/v1/forecast`
- **Authentication**: **None** (Open access API)
- **Rate Limits**: Up to 10,000 API calls per day for non-commercial educational use.

### Micro-Zone Monitoring Coordinates (Kerala):
| District / Location | Latitude | Longitude | Critical Risk Factor |
| :--- | :--- | :--- | :--- |
| **Wayanad (Vythiri / Mundakkai)** | `11.55` | `76.04` | Severe Landslide Zone (2024 debris flow) |
| **Idukki (Munnar / Pettimudi)** | `10.08` | `77.06` | High-Altitude Extreme Rainfall Zone |
| **Kottayam (Teekoy / Meenachil)** | `9.68` | `76.82` | Flash Flood & Hill Slope Washout Zone |

### Example API Request:
```http
GET https://api.open-meteo.com/v1/forecast?latitude=11.55&longitude=76.04&hourly=precipitation,rain&past_days=3&forecast_days=1&timezone=Asia%2FKolkata
```

---

## 5. ☁️ Google Cloud Platform (GCP) Compute Engine Always Free Setup

Google Cloud Console provides a **100% Always Free Tier** featuring 1 Compute Engine `e2-micro` Virtual Machine instance, 30 GB standard persistent disk, and 1 GB monthly outbound egress at ₹0/month forever.

### Step 5.1: Create GCP Billing Account & Project
1. Visit **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Sign in with your Google account and create a new project named `malabar-watch-prod`.
3. Enable billing (requires credit card for identity verification; no charges will occur within Always Free limits).

### Step 5.2: Generate SSH Keypair (Local Terminal)
Run the following command on your local machine to generate an SSH keypair:

**Linux / macOS (Bash/Zsh):**
```bash
mkdir -p ~/.ssh
ssh-keygen -t ed25519 -C "malabar-watch-gcp" -f ~/.ssh/id_ed25519_malabar_gcp
```

**Windows (PowerShell):**
```powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force
ssh-keygen -t ed25519 -C "malabar-watch-gcp" -f "$env:USERPROFILE\.ssh\id_ed25519_malabar_gcp"
```

This generates two files:
- Private Key: `id_ed25519_malabar_gcp` (Keep confidential!)
- Public Key: `id_ed25519_malabar_gcp.pub` (Upload to GCP)

### Step 5.3: Provision Always Free `e2-micro` VM Instance
1. Go to **Compute Engine** ➔ **VM Instances** ➔ **Create Instance**.
2. **Name**: `malabar-watch-vm-01`.
3. **Region**: Select an Always Free Region:
   - `us-central1` (Iowa)
   - `us-east1` (South Carolina)
   - `us-west1` (Oregon)
4. **Machine Family**: General-purpose ➔ Series `E2` ➔ Machine Type `e2-micro` (0.25–2 vCPU, 1 GB RAM).
5. **Boot Disk**: Click **Change** ➔ Operating System: `Ubuntu` (or `Debian`) ➔ Boot Disk Type: **Standard persistent disk** (do NOT use *Balanced persistent disk*) ➔ Size: `30 GB`.
6. **SSH Keys**: Expand **Advanced Options** ➔ **Security** ➔ **SSH Keys** ➔ Paste contents of `id_ed25519_malabar_gcp.pub`.
7. Click **Create**. Note down the assigned **External Public IP**.

> 💡 **Why does GCP Console show "Monthly estimate US$7.11"?**  
> Google Cloud Console always displays the baseline list price before applying the **Always Free Tier discount**. As long as your instance is `e2-micro` in `us-central1`, `us-east1`, or `us-west1`, and uses **Standard persistent disk** (up to 30 GB), GCP automatically credits **$7.11/month (100% discount)** on your bill, resulting in **$0.00 actual cost**.

### Step 5.4: Configure 2 GB Swap File on Ubuntu VM
Since `e2-micro` has 1 GB RAM, configure a 2 GB Linux Swap file to prevent memory pressure during Python dependency installation:
```bash
ssh -i ~/.ssh/id_ed25519_malabar_gcp ubuntu@<YOUR_VM_PUBLIC_IP>

# Inside VM:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 6. 🔐 GitHub Secrets & Actions CI/CD Setup

To automate testing, linting, and continuous deployment, store all sensitive production keys in your GitHub repository's encrypted secrets store.

### Step-by-Step Guide:
1. Open your repository on GitHub.
2. Go to **Settings** ➔ **Secrets and variables** ➔ **Actions**.
3. Click **New repository secret** for each item below:

| Secret Name | Value Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key (`AIzaSy...`) |
| `GROQ_API_KEY` | Groq API Key (`gsk_...`) |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from BotFather |
| `TELEGRAM_CHAT_ID` | Telegram Channel or Group Chat ID (`-100...`) |
| `GCP_HOST` | GCP Compute Engine VM Public IP Address |
| `GCP_SSH_KEY` | Contents of `~/.ssh/id_ed25519_malabar_gcp` (Private Key) |

---

## 7. 🛠️ Complete `.env` File Reference

Create a file named `.env` in the root of your project directory for local testing. **Never commit `.env` to Git** (it is protected by `.gitignore`).

```ini
# ==============================================================================
# Malabar Watch - Environment Configuration
# ==============================================================================

# Application Meta
ENVIRONMENT="development"  # Options: development, staging, production
LOG_LEVEL="INFO"           # Options: DEBUG, INFO, WARNING, ERROR

# LLM Providers
GEMINI_API_KEY="AIzaSyYourGeneratedGeminiKeyHere"
GROQ_API_KEY="gsk_YourGeneratedGroqKeyHere"

# Telegram Notification Bot
TELEGRAM_BOT_TOKEN="7890123456:AAFdYourTelegramTokenHere"
TELEGRAM_CHAT_ID="-1001234567890"

# Database Configuration
DATABASE_URL="sqlite:///malabar_watch.sqlite"

# Ingestion Settings
OPEN_METEO_BASE_URL="https://api.open-meteo.com/v1/forecast"
INGESTION_INTERVAL_MINUTES=60

# Risk Threshold Defaults (mm)
RAINFALL_WARNING_THRESHOLD_24H=100.0
RAINFALL_HIGH_RISK_THRESHOLD_24H=150.0
RAINFALL_EXTREME_THRESHOLD_24H=204.4
ANTECEDENT_PRECIPITATION_INDEX_ALPHA=0.85
```
