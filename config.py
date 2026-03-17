"""
config.py — Load and validate all configuration from environment variables.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()


def get_required(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Missing required environment variable: {key}\n"
            f"Check your .env file (see .env.example for reference)."
        )
    return value


# ── Ollama cloud ──────────────────────────────────────────────────────────────
OLLAMA_API_KEY: str = get_required("OLLAMA_API_KEY")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "glm-5:cloud")
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "https://ollama.com")

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID: str = get_required("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: str = get_required("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER: str = get_required("TWILIO_FROM_NUMBER")
WHATSAPP_TO_NUMBER: str = get_required("WHATSAPP_TO_NUMBER")

# ── Feeds ─────────────────────────────────────────────────────────────────────
FEEDS_CONFIG_PATH: str = os.getenv("FEEDS_CONFIG_PATH", "feeds_config.json")

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
