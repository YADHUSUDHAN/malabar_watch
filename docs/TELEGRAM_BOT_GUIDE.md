# Telegram Bot Guide & Setup Instructions - Malabar Watch

This document provides step-by-step instructions for creating, configuring, and running the **Malabar Watch Telegram Bot**.

---

## 1. Creating the Telegram Bot via BotFather

1. Open the **Telegram** app on your phone or desktop.
2. Search for `@BotFather` and start a chat.
3. Send the command: `/newbot`
4. Enter a display name for your bot, e.g.:
   `Malabar Watch Alert Bot`
5. Enter a unique username ending in `bot`, e.g.:
   `malabar_watch_bot` or `malabar_watch_alert_bot`
6. **BotFather** will generate a HTTP API access token. It will look like:
   `7890123456:AAFgH_example_token_abcdef12345`
7. Save this token securely! You will add it as an environment variable (`TELEGRAM_BOT_TOKEN`).

---

## 2. Configuring Bot Commands in BotFather

Send `/setcommands` to `@BotFather`, select your bot, and paste the following list of commands:

```text
status - Check real-time risk status for a district (e.g. /status wayanad)
subscribe - Subscribe to automated rainfall & landslide alerts
unsubscribe - Stop receiving automated alert notifications
history - View past 72-hour rainfall totals for a district
disclaimer - Read the official educational & portfolio disclaimer
help - Get instructions on how to use Malabar Watch
```

---

## 3. Bot Command Architecture & User Interactions

### 3.1 Command Overview

| Command | Usage | Description |
|---|---|---|
| `/start` | `/start` | Welcome message, safety disclaimer, interactive district selection menu. |
| `/status [district]` | `/status wayanad`, `/status idukki`, `/status kottayam` | Fetches real-time cumulative rainfall, risk score, and LLM bilingual summary. |
| `/subscribe [district]` | `/subscribe wayanad` or `/subscribe all` | Subscribes the user's Chat ID to automated warning pushes. |
| `/unsubscribe` | `/unsubscribe` | Deactivates subscription for the chat. |
| `/history [district]` | `/history wayanad` | Displays tabular 24h/48h/72h rainfall trend. |
| `/disclaimer` | `/disclaimer` | Displays project scope and safety disclaimers. |

---

## 4. Sample Bilingual Alert Output

When an automated push or `/status` request is triggered, the bot generates a structured message formatted in Telegram HTML:

```html
🚨 <b>MALABAR WATCH WARNING | മലബാർ വാച്ച് മുന്നറിയിപ്പ്</b>
───────────────────────────
📍 <b>District:</b> Wayanad (വയനാട് - വൈത്തിരി / ചൂരൽമല)
⚠️ <b>Risk Level:</b> ORANGE ALERT (ഓറഞ്ച് അലർട്ട് - HIGH RISK)
🌧️ <b>Rainfall Stats:</b>
  • Last 24 hours: 142.5 mm
  • Last 48 hours: 218.0 mm
  • Antecedent Saturation (API): High (ഉയർന്ന പൂരിതത്വം)

───────────────────────────
<b>English Summary & Advisory:</b>
Heavy continuous rainfall recorded across Wayanad hills over the last 48 hours. Soil saturation levels match patterns observed prior to localized slope failures.
👉 <i>Action: Avoid travel through hilly mountain passes. Residents near steep cut slopes should prepare for precautionary relocation.</i>

───────────────────────────
<b>മലയാളം ചുരുക്കവും നിർദ്ദേശവും:</b>
കഴിഞ്ഞ 48 മണിക്കൂറായി വയനാടൻ മലയോര മേഖലകളിൽ ശക്തമായ മഴ തുടരുന്നു. മണ്ണിൽ ജലാംശം ഉയർന്ന അളവിലാണ്.
👉 <i>നിർദ്ദേശം: മലയോര മേഖലകളിലേക്കുള്ള യാത്ര ഒഴിവാക്കുക. ചരിവുള്ള പ്രദേശങ്ങളിൽ താമസിക്കുന്നവർ ജാഗ്രത പാലിക്കുകയും സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറാൻ തയ്യാറാവുകയും ചെയ്യുക.</i>

───────────────────────────
⚠️ <i>Note: Educational/portfolio project. Always follow official IMD & KSDMA alerts.</i>
```

---

## 5. Local Dry-Run Testing (Without Telegram Account)

During development, you can run the bot in dry-run mode, which logs responses to the console without sending actual messages:

```bash
# Set environment variables
export TELEGRAM_BOT_TOKEN="mock_token_for_dev"
export GEMINI_API_KEY="your_gemini_key"
export GROQ_API_KEY="your_groq_key"

# Run dry-run simulation
python -m src.main --dry-run --district wayanad
```
