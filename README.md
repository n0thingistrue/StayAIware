# StayAIware

Automated daily news briefing — RSS feeds → GLM-5 (Ollama cloud) → WhatsApp.
Runs every morning at 08:00 via cron. Bilingual output (English + French).

---

## Project Structure

```
StayAIware/
├── src/
│   ├── config.py          # Loads .env, validates required variables
│   ├── feeds.py           # Fetches and parses RSS feeds (round-robin by category)
│   ├── summarizer.py      # Calls Ollama GLM-5 cloud, returns formatted brief
│   ├── whatsapp.py        # Sends via Twilio (splits messages at section boundaries)
│   └── openclaw.py        # Sends via OpenClaw self-hosted gateway
├── deploy/
│   ├── docker-compose.yml # OpenClaw container setup
│   └── setup_openclaw.sh  # OpenClaw deploy + WhatsApp linking script
├── main.py                # Entry point
├── feeds_config.json      # RSS feed list
├── setup.sh               # Python environment installer
├── requirements.txt
└── .env.example
```

---

## Prerequisites

| Requirement | Where to get it |
|---|---|
| Python 3.10+ | `sudo apt install python3 python3-venv` |
| Ollama API key | https://ollama.com/settings/keys |
| Twilio account (optional) | https://www.twilio.com/console |
| Docker (for OpenClaw) | https://docs.docker.com/engine/install/ |

---

## Quick Start

```bash
git clone https://github.com/n0thingistrue/StayAIware.git
cd StayAIware
bash setup.sh
```

`setup.sh` creates a `.venv`, installs dependencies, and copies `.env.example` to `.env`.

---

## Configuration

Edit `.env`:

```env
# Ollama cloud (https://ollama.com/settings/keys)
OLLAMA_API_KEY=your-key-here
OLLAMA_MODEL=glm-5:cloud
OLLAMA_HOST=https://ollama.com

# Twilio WhatsApp (optional fallback)
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=your_token
TWILIO_FROM_NUMBER=whatsapp:+14155238886

# Personal number OR WhatsApp group ID (e.g. 120363XXXXXXXXXX@g.us)
WHATSAPP_TO_NUMBER=whatsapp:+YOUR_PHONE_NUMBER
```

---

## Usage

```bash
# Dry run — generates brief, prints to terminal, sends nothing
.venv/bin/python main.py --dry-run

# Send via Twilio
.venv/bin/python main.py

# Send via OpenClaw (self-hosted WhatsApp gateway)
.venv/bin/python main.py --openclaw
```

---

## OpenClaw Setup (self-hosted WhatsApp)

OpenClaw replaces Twilio — it connects directly to your WhatsApp account via QR scan.

**1. Start the container:**
```bash
bash deploy/setup_openclaw.sh
```

**2. Enable the WhatsApp plugin and scan the QR code:**
```bash
bash deploy/setup_openclaw.sh --link
```

Scan the QR with your phone:
`WhatsApp → Settings → Linked Devices → Link a Device`

The session is saved in a Docker volume — no need to re-scan after restarts.

**3. Test:**
```bash
docker exec openclaw openclaw message send --channel whatsapp --target +YOUR_PHONE_NUMBER --message "Test OK"
```

**Other modes:**
```bash
bash deploy/setup_openclaw.sh --restart   # restart container
bash deploy/setup_openclaw.sh --logs      # follow logs
```

---

## Cron (08:00 daily)

```bash
crontab -e
```

```
0 8 * * * cd /opt/stayaiware && .venv/bin/python main.py --openclaw >> logs/cron.log 2>&1
```

---

## RSS Sources

30 feeds across 7 categories — balanced round-robin selection, filtered to last 24h:

| Category | Sources |
|---|---|
| Geopolitics | BBC World Europe, BBC World, The Guardian, Al Jazeera, Reuters, France 24 |
| Global Economy | BBC Business, The Guardian Business & Economics, NPR Economy |
| Crypto | CoinDesk, CoinTelegraph, Decrypt, The Block |
| Tech | BBC Tech, TechCrunch, Wired, Ars Technica |
| Positive News | Good News Network, Positive News, Reasons to be Cheerful, Yes! Magazine |
| AI | The Verge AI, VentureBeat AI, TechCrunch AI |
| Cyber | Krebs on Security, The Hacker News, Bleeping Computer, Dark Reading, SecurityWeek |

Edit `feeds_config.json` to add/remove sources or change `active_categories` to filter by category.

---

## Logs

| File | Content |
|---|---|
| `logs/daily_brief.log` | Full run log |
| `logs/cron.log` | Cron output |

---

## Output Format

```
🌍 DAILY GLOBAL BRIEF
Date: Monday, March 17 2026

─────────────────────────
TOPIC TITLE

🇬🇧 English summary (2-3 sentences)

🇫🇷 French summary (2-3 sentences)

💬 Conversation starter question
─────────────────────────
[× 4 stories]

🧠 Word of the Day
• Word: ...
• French: ...
• Example: ...
```
