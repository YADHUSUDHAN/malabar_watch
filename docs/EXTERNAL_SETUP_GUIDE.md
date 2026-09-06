# External Services & Infrastructure Setup Guide

This document provides complete, step-by-step instructions for provisioning all required external services, obtaining API credentials, creating Telegram alert bots, configuring zero-cost cloud hosting on Amazon Web Services (AWS) EC2 Free Tier with AWS Systems Manager (SSM), and setting up GitHub Actions secrets for **Malabar Watch (മലബാർ വാച്ച്)**.

---

## 📋 Summary of Required External Credentials

| Service | Purpose | Key / Secret Name | Cost |
| :--- | :--- | :--- | :--- |
| **Google AI Studio** | Primary LLM Reasoning Gateway | `GEMINI_API_KEY` | Free Tier available |
| **Groq Cloud** | Failover LLM Gateway | `GROQ_API_KEY` | Free Tier available |
| **Telegram BotFather** | Outbound Alert Dispatcher | `TELEGRAM_BOT_TOKEN` | Free |
| **Telegram Channel / User** | Target Alert Recipient | `TELEGRAM_CHAT_ID` | Free |
| **Open-Meteo API** | Weather & Rainfall Data Source | *None (No Key Needed)* | Free / Open Access |
| **AWS EC2 Free Tier** | Cloud VM (`t2.micro`/`t3.micro` in `ap-south-1`) | AWS Systems Manager (SSM) | ₹0/month (Free Tier) |
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

## 5. ☁️ Amazon Web Services (AWS) Free Tier & Systems Manager (SSM) Setup

> 💡 **Notice: Local-First Workflow**  
> Complete all local development, testing (`uv run pytest`), and verification before provisioning AWS cloud infrastructure.

AWS provides **750 hours/month** of Linux `t2.micro` or `t3.micro` under the 12-Month Free Tier:

### Step 5.1: Create IAM Role for Keyless AWS SSM Access
1. Open the **[AWS IAM Console](https://console.aws.amazon.com/iam/)**.
2. Navigate to **Roles** ➔ **Create role**.
3. Select **AWS service** ➔ Use case: **EC2**.
4. Attach permission policy: `AmazonSSMManagedInstanceCore`.
5. Name the role: `malabar-watch-ssm-role` and click **Create role**.

### Step 5.2: Create Zero-Inbound Security Group
1. Open **EC2 Console** ➔ **Security Groups** ➔ **Create security group**.
2. Name: `malabar-watch-zero-inbound`.
3. Inbound rules: **Leave completely empty** (Deny all inbound traffic from `0.0.0.0/0`).
4. Outbound rules: **All traffic** (allowing outbound HTTPS 443 for Open-Meteo, Telegram, and LLM APIs).

### Step 5.3: Launch AWS EC2 Free Tier Instance
1. In EC2 Console, choose region **Asia Pacific (Mumbai) `ap-south-1`**.
2. Click **Launch Instance**:
   - **Name**: `malabar-watch-node-01`
   - **AMI**: `Ubuntu Server 24.04 LTS (HVM), SSD Volume Type`
   - **Instance Type**: `t2.micro` or `t3.micro` (Free Tier eligible)
   - **Key pair**: *Proceed without a key pair* (keyless access via SSM)
   - **Network settings**: Select the `malabar-watch-zero-inbound` Security Group.
   - **Configure Storage**: `30 GiB` gp3 root volume.
   - **Advanced Details**: In **IAM instance profile**, select `malabar-watch-ssm-role`.
3. Click **Launch Instance**.

### Step 5.4: Connect Keylessly via AWS SSM & Configure Swap
1. Once the instance status is *Running*, select it and click **Connect** ➔ **Session Manager** ➔ **Connect**.
2. Configure a 2 GB Linux Swap file:
   ```bash
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

---

## 6. 🔐 GitHub Secrets & Actions CI/CD Setup

Store sensitive API keys in your GitHub repository's encrypted secrets store:
1. Open your repository on GitHub.
2. Go to **Settings** ➔ **Secrets and variables** ➔ **Actions**.
3. Add the following secrets:

| Secret Name | Value Description |
| :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key (`AIzaSy...`) |
| `GROQ_API_KEY` | Groq API Key (`gsk_...`) |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token from BotFather |
| `TELEGRAM_CHAT_ID` | Telegram Channel or Group Chat ID (`-100...`) |
| `AWS_ROLE_ARN` | AWS IAM Role ARN configured for GitHub OIDC |
| `AWS_REGION` | AWS Region (e.g., `ap-south-1`) |
| `AWS_INSTANCE_ID` | Target EC2 Instance ID (`i-...`) |

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
