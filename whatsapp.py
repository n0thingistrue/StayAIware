"""
whatsapp.py — Send a message via the Twilio WhatsApp API.

Twilio sandbox hard limit: 1600 chars per message.
Long briefs are automatically split at section boundaries (never mid-paragraph)
and sent as sequential messages with a short delay between them.
"""

import logging
import time

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

import config

logger = logging.getLogger(__name__)

# Stay well below the 1600-char Twilio hard limit.
TWILIO_MAX_CHARS = 1550

# Separator used in the brief to delimit story blocks.
SECTION_SEP = "─────────────────────────"


def _split_into_parts(message: str) -> list[str]:
    """
    Split the brief into a list of strings, each under TWILIO_MAX_CHARS.

    Strategy:
    1. Break the text at every SECTION_SEP boundary to get logical blocks.
    2. Greedily pack consecutive blocks into one part until adding the next
       block would exceed the limit — then start a new part.
    This guarantees no story is ever split mid-paragraph.
    """
    # Re-attach the separator at the start of each block so the formatting
    # is preserved when parts are sent independently.
    raw_blocks = message.split(SECTION_SEP)

    blocks: list[str] = []
    for i, block in enumerate(raw_blocks):
        block = block.strip()
        if not block:
            continue
        # Restore the separator for every block except the first (header).
        if i > 0:
            block = SECTION_SEP + "\n\n" + block
        blocks.append(block)

    if not blocks:
        return [message]

    parts: list[str] = []
    current = blocks[0]

    for block in blocks[1:]:
        candidate = current + "\n\n" + block
        if len(candidate) <= TWILIO_MAX_CHARS:
            current = candidate
        else:
            parts.append(current)
            current = block

    parts.append(current)
    return parts


def send_whatsapp(message: str) -> list[str]:
    """
    Send the brief to the configured WhatsApp number via Twilio.
    If the message exceeds TWILIO_MAX_CHARS it is split into multiple parts
    sent sequentially. Returns a list of Twilio message SIDs.
    """
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    parts = _split_into_parts(message)

    logger.info(
        "Sending to %s in %d part(s) (total %d chars).",
        config.WHATSAPP_TO_NUMBER,
        len(parts),
        len(message),
    )

    sids: list[str] = []
    for i, part in enumerate(parts, start=1):
        logger.info("Sending part %d/%d (%d chars)…", i, len(parts), len(part))
        msg = client.messages.create(
            body=part,
            from_=config.TWILIO_FROM_NUMBER,
            to=config.WHATSAPP_TO_NUMBER,
        )
        logger.info("Part %d sent. SID: %s  Status: %s", i, msg.sid, msg.status)
        sids.append(msg.sid)

        # Brief pause between parts so messages arrive in order.
        if i < len(parts):
            time.sleep(1)

    return sids
