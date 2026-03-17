"""
summarizer.py — Send collected headlines to GLM-5 via Ollama cloud API
                and return the formatted Daily Global Brief.

Requires an Ollama account + API key: https://ollama.com/settings/keys
Model used: glm-5:cloud  (equivalent to `ollama run glm-5:cloud`)
"""

import logging
from datetime import date

from ollama import Client

import config

logger = logging.getLogger(__name__)

# WhatsApp messages are capped at 4096 chars.
MAX_BRIEF_CHARS = 3800

SYSTEM_PROMPT = """\
You are a world-class multilingual news editor who writes a daily briefing
called "Daily Global Brief". Your audience are curious, educated adults who
want to stay informed quickly.

Rules:
- Select the 4 most globally significant or interesting stories from the list.
- Prefer variety: try to cover different categories (geopolitics, tech, economy,
  crypto, positive news).
- Summaries must be factual, neutral, and accessible to non-experts.
- French summaries must be natural, idiomatic French — not a word-for-word
  translation.
- Conversation starters should be open, curious questions that anyone could
  ask a friend.
- The Word of the Day must be a real English word with a French translation and
  an example sentence.
- Do NOT invent facts. Only use what is in the provided headlines.
- Keep the total output under {max_chars} characters (WhatsApp message limit).
""".format(max_chars=MAX_BRIEF_CHARS)


def _build_user_prompt(headlines_text: str, today: str) -> str:
    return f"""\
Today is {today}.

Below is a numbered list of news headlines collected this morning from various
RSS feeds. Select the 4 most important/interesting ones and write the
Daily Global Brief in the exact format shown.

--- HEADLINES ---
{headlines_text}
--- END OF HEADLINES ---

Output the brief using EXACTLY this format (keep the emoji, keep the
section labels):

🌍 DAILY GLOBAL BRIEF
Date: {today}

[Repeat the block below 4 times, once per story]

─────────────────────────
[TOPIC TITLE IN CAPS]

🇬🇧 [2-3 sentence English summary]

🇫🇷 [2-3 sentence French summary]

💬 [Conversation starter question]
─────────────────────────

🧠 Word of the Day
• Word: [english word]
• French: [traduction française]
• Example: [one sentence using the word naturally]
"""


def generate_brief(headlines_text: str) -> str:
    """
    Call the Ollama cloud API (glm-5:cloud) and return the formatted brief.
    Raises on connection or API errors.
    """
    today = date.today().strftime("%A, %B %d %Y")

    client = Client(
        host=config.OLLAMA_HOST,
        headers={"Authorization": f"Bearer {config.OLLAMA_API_KEY}"},
    )

    logger.info(
        "Sending %d chars of headlines to %s via %s…",
        len(headlines_text),
        config.OLLAMA_MODEL,
        config.OLLAMA_HOST,
    )

    response = client.chat(
        model=config.OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(headlines_text, today)},
        ],
        options={"temperature": 0.4},
    )

    brief = response["message"]["content"].strip()
    logger.info("Ollama returned %d characters.", len(brief))

    if len(brief) > MAX_BRIEF_CHARS:
        logger.warning(
            "Brief (%d chars) exceeds WhatsApp limit (%d). Truncating.",
            len(brief),
            MAX_BRIEF_CHARS,
        )
        brief = brief[:MAX_BRIEF_CHARS - 3] + "..."

    return brief
