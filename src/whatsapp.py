"""
whatsapp.py — Send a message via the Twilio WhatsApp API.

Twilio sandbox hard limit: 1600 chars per message.
Long briefs are split at section boundaries and sent sequentially.
"""

import logging
import time

from twilio.rest import Client

from . import config

logger = logging.getLogger(__name__)

TWILIO_MAX_CHARS = 1550
SECTION_SEP = "─────────────────────────"


def _split_into_parts(message: str) -> list[str]:
    raw_blocks = message.split(SECTION_SEP)

    blocks: list[str] = []
    for i, block in enumerate(raw_blocks):
        block = block.strip()
        if not block:
            continue
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

        if i < len(parts):
            time.sleep(1)

    return sids
