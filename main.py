"""
main.py — Entry point for the Daily Global Brief system.

Usage:
    python main.py                   # send via Twilio (default)
    python main.py --openclaw        # send via OpenClaw (Docker), fallback Twilio
    python main.py --dry-run         # print brief to stdout, send nothing
    python main.py --dry-run --openclaw  # dry-run + show which sender would be used
"""

import argparse
import logging
import sys
from pathlib import Path

# Ensure logs/ directory exists before anything else logs to a file.
Path("logs").mkdir(exist_ok=True)

# Add a file handler so cron captures all output.
file_handler = logging.FileHandler("logs/daily_brief.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logging.getLogger().addHandler(file_handler)

# config import triggers .env loading and logging setup.
import config  # noqa: E402
import feeds as feeds_module
import summarizer
import whatsapp
import openclaw as openclaw_module

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily Global Brief — fetch news, summarise with AI, send via WhatsApp."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the brief but print it to stdout instead of sending it.",
    )
    parser.add_argument(
        "--openclaw",
        action="store_true",
        help="Send via OpenClaw (Docker) instead of Twilio. Falls back to Twilio on error.",
    )
    return parser.parse_args()


def _send(brief: str, use_openclaw: bool) -> None:
    """Deliver the brief. OpenClaw is tried first when requested; Twilio is the fallback."""
    if use_openclaw:
        try:
            n = openclaw_module.send_openclaw(brief)
            logger.info("OpenClaw: %d part(s) sent successfully.", n)
            return
        except Exception as exc:
            logger.warning("OpenClaw failed (%s) — falling back to Twilio.", exc)

    sids = whatsapp.send_whatsapp(brief)
    logger.info("Twilio: %d message(s) sent. SIDs: %s", len(sids), sids)


def run(dry_run: bool = False, use_openclaw: bool = False) -> None:
    sender_label = "OpenClaw → Twilio fallback" if use_openclaw else "Twilio"
    logger.info("=== Daily Global Brief starting (sender: %s) ===", sender_label)

    # 1. Collect news
    logger.info("Step 1/3: Fetching RSS feeds…")
    articles = feeds_module.fetch_all_articles()
    if not articles:
        logger.error("No articles collected. Aborting.")
        sys.exit(1)

    headlines_text = feeds_module.articles_to_prompt_text(articles)
    logger.info("Headlines ready (%d articles, %d chars).", len(articles), len(headlines_text))

    # 2. Generate brief with Ollama / GLM-5
    logger.info("Step 2/3: Generating brief with %s…", config.OLLAMA_MODEL)
    try:
        brief = summarizer.generate_brief(headlines_text)
    except Exception as exc:
        logger.exception("Ollama API call failed: %s", exc)
        sys.exit(1)

    # 3. Send (or print in dry-run mode)
    if dry_run:
        logger.info("Step 3/3: DRY RUN — printing brief to stdout.")
        sender_info = f"[would use: {'OpenClaw → fallback Twilio' if use_openclaw else 'Twilio'}]"
        print("\n" + "=" * 60)
        print(brief)
        print("=" * 60)
        print(f"[dry-run] length: {len(brief)} chars  {sender_info}\n")
    else:
        logger.info("Step 3/3: Sending via %s…", sender_label)
        try:
            _send(brief, use_openclaw)
        except Exception as exc:
            logger.exception("All send attempts failed: %s", exc)
            sys.exit(1)

    logger.info("=== Daily Global Brief complete ===")


if __name__ == "__main__":
    args = parse_args()
    run(dry_run=args.dry_run, use_openclaw=args.openclaw)
