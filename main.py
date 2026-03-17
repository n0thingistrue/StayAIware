"""
main.py — Entry point for StayAIware.

Usage:
    python main.py                   # send via Twilio (default)
    python main.py --openclaw        # send via OpenClaw, fallback Twilio
    python main.py --dry-run         # print brief, send nothing
    python main.py --dry-run --openclaw
"""

import argparse
import logging
import sys
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

file_handler = logging.FileHandler("logs/daily_brief.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logging.getLogger().addHandler(file_handler)

from src import config
from src import feeds as feeds_module
from src import summarizer
from src import whatsapp
from src import openclaw as openclaw_module

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="StayAIware — daily AI news briefing.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print brief to stdout, do not send.")
    parser.add_argument("--openclaw", action="store_true",
                        help="Send via OpenClaw instead of Twilio (fallback to Twilio on error).")
    return parser.parse_args()


def _send(brief: str, use_openclaw: bool) -> None:
    if use_openclaw:
        try:
            n = openclaw_module.send_openclaw(brief)
            logger.info("OpenClaw: %d part(s) sent.", n)
            return
        except Exception as exc:
            logger.warning("OpenClaw failed (%s) — falling back to Twilio.", exc)

    sids = whatsapp.send_whatsapp(brief)
    logger.info("Twilio: %d message(s) sent. SIDs: %s", len(sids), sids)


def run(dry_run: bool = False, use_openclaw: bool = False) -> None:
    sender = "OpenClaw → Twilio fallback" if use_openclaw else "Twilio"
    logger.info("=== StayAIware starting (sender: %s) ===", sender)

    logger.info("Step 1/3: Fetching RSS feeds…")
    articles = feeds_module.fetch_all_articles()
    if not articles:
        logger.error("No articles collected. Aborting.")
        sys.exit(1)

    headlines_text = feeds_module.articles_to_prompt_text(articles)
    logger.info("Headlines ready (%d articles, %d chars).", len(articles), len(headlines_text))

    logger.info("Step 2/3: Generating brief with %s…", config.OLLAMA_MODEL)
    try:
        brief = summarizer.generate_brief(headlines_text)
    except Exception as exc:
        logger.exception("Ollama API call failed: %s", exc)
        sys.exit(1)

    if dry_run:
        logger.info("Step 3/3: DRY RUN — printing brief to stdout.")
        print("\n" + "=" * 60)
        print(brief)
        print("=" * 60)
        print(f"\n[dry-run] {len(brief)} chars  |  sender: {sender}\n")
    else:
        logger.info("Step 3/3: Sending via %s…", sender)
        try:
            _send(brief, use_openclaw)
        except Exception as exc:
            logger.exception("All send attempts failed: %s", exc)
            sys.exit(1)

    logger.info("=== StayAIware complete ===")


if __name__ == "__main__":
    args = parse_args()
    run(dry_run=args.dry_run, use_openclaw=args.openclaw)
