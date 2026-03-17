# 🌍 Daily Global Brief

A Python automation system that runs every day at 08:00, collects news from RSS feeds, generates a bilingual (English + French) briefing using Claude AI, and sends it to your WhatsApp via Twilio.

---

## Project Structure

```
daily-global-brief/
├── main.py              # Entry point — orchestrates the full pipeline
├── config.py            # Loads .env, validates required vars
├── feeds.py             # Fetches and parses RSS feeds
├── summarizer.py        # Sends headlines to Claude, returns formatted brief
├── whatsapp.py          # Sends the message via Twilio WhatsApp API
├── feeds_config.json    # RSS feed list (edit to add/remove sources)
├── requirements.txt     # Python dependencies
├── setup.sh             # One-shot installer
├── .env.example         # Template — copy to .env and fill in your keys
├── .gitignore
└── logs/                # Auto-created; stores daily_brief.log & cron.log
```

---

## Prerequisites

| Requirement | Where to get it |
|---|---|
| Python 3.10+ | `sudo apt install python3 python3-venv` |
| Anthropic API key | https://console.anthropic.com |
| Twilio account + WhatsApp sandbox | https://www.twilio.com/console |
| Your WhatsApp number | Your phone |

---

## 1. Install (Local — Linux Mint)

```bash
# Clone or copy the project folder, then:
cd daily-global-brief
bash setup.sh
```

`setup.sh` will:
- Create a `.venv` virtual environment
- Install all Python packages
- Copy `.env.example` → `.env`
- Print the cron line to paste

---

## 2. Configure API Keys

Edit `.env` (created by setup.sh):

```env
ANTHROPIC_API_KEY=sk-ant-...
TWILIO_ACCOUNT_SID=ACxxxx...
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=whatsapp:+14155238886
WHATSAPP_TO_NUMBER=whatsapp:+33612345678
```

### Getting Twilio WhatsApp credentials

1. Sign up at https://www.twilio.com (free tier works)
2. In the console → **Messaging → Try it out → Send a WhatsApp message**
3. You'll get a sandbox number (e.g. `+14155238886`) and a join code
4. Send the join code from YOUR WhatsApp to activate the sandbox
5. Copy your Account SID and Auth Token from the dashboard

---

## 3. Test a Dry Run

```bash
.venv/bin/python main.py --dry-run
```

This runs the full pipeline (fetches feeds, calls Claude) but **prints the brief to your terminal instead of sending it**.
Use this to verify everything works before enabling the cron job.

---

## 4. Send a Real Message (Manual Test)

```bash
.venv/bin/python main.py
```

Check your WhatsApp — you should receive the brief within seconds.

---

## 5. Schedule with Cron (08:00 every day)

```bash
crontab -e
```

Add this line (replace `/path/to/daily-global-brief` with your actual path):

```
0 8 * * * cd /path/to/daily-global-brief && .venv/bin/python main.py >> logs/cron.log 2>&1
```

Verify cron is running:

```bash
grep CRON /var/log/syslog | tail -20
# or:
tail -f logs/cron.log
```

---

## 6. Deploy on a VPS

```bash
# 1. Copy project to VPS
scp -r daily-global-brief user@your-vps-ip:~/

# 2. SSH in and run setup
ssh user@your-vps-ip
cd daily-global-brief
bash setup.sh

# 3. Fill in .env on the VPS
nano .env

# 4. Test
.venv/bin/python main.py --dry-run

# 5. Add cron (same as above)
crontab -e
```

For VPS, also make sure the system timezone is correct:

```bash
timedatectl set-timezone Europe/Paris   # or your timezone
```

---

## Customising RSS Feeds

Edit `feeds_config.json` to add, remove, or adjust sources:

```json
{
  "feeds": [
    {
      "name": "My Custom Feed",
      "url": "https://example.com/rss",
      "category": "tech"
    }
  ],
  "max_articles_per_feed": 5,
  "max_total_articles": 35
}
```

Valid categories: `geopolitics`, `tech`, `economy`, `crypto`, `positive`

---

## Logs

| File | Content |
|---|---|
| `logs/daily_brief.log` | Detailed run log (from Python logging) |
| `logs/cron.log` | stdout/stderr captured by cron |

---

## Example Output

```
🌍 DAILY GLOBAL BRIEF
Date: Monday, March 16 2026

─────────────────────────
G7 AGREES NEW SANCTIONS ON CRITICAL MINERALS

🇬🇧 G7 finance ministers reached a deal on Sunday to impose coordinated
export controls on critical minerals used in battery and chip production.
The agreement targets shipments to countries deemed strategic rivals.

🇫🇷 Les ministres des finances du G7 ont conclu dimanche un accord pour
instaurer des contrôles coordonnés sur les exportations de minéraux
critiques. L'accord cible les livraisons vers des pays considérés comme
des rivaux stratégiques.

💬 Do you think export controls on minerals could spark a new trade war?
─────────────────────────
...

🧠 Word of the Day
• Word: Resilience
• French: Résilience
• Example: The company showed remarkable resilience after the cyber attack.
```

---

## Future Improvements

### Near-term
- **Smarter filtering** — score headlines by recency + keyword importance before sending to Claude, so you always get the freshest stories.
- **Topic deduplication** — cluster similar headlines (e.g. two Reuters/BBC stories on the same event) and merge them into one entry before the AI prompt, saving tokens.
- **Retry logic** — if a feed is down or Claude returns an error, retry up to 3 times with exponential back-off.

### Medium-term
- **"Question of the Day" for English practice** — add a dedicated section where Claude generates a grammar or vocabulary exercise based on the day's news vocabulary.
- **Category weighting** — let the user configure how many stories per category they want (e.g. always 1 crypto, 2 geopolitics, 1 positive).
- **Telegram / Signal fallback** — if WhatsApp delivery fails, re-send via a second channel.
- **Web archive** — save each brief as a dated `.txt` file in `archive/` so you can review past editions.

### Long-term
- **Personalisation** — let the user provide a list of tracked keywords (companies, countries, topics) and have Claude flag stories that match.
- **Multi-language expansion** — add Spanish, German, or Arabic output by changing the system prompt.
- **Dashboard** — a minimal Flask/FastAPI endpoint that shows the last 7 briefs as HTML.
