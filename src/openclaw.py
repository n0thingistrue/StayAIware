"""
openclaw.py — Send the daily brief via OpenClaw (self-hosted WhatsApp gateway).

OpenClaw exposes no HTTP endpoint for outbound messages — uses CLI:
    openclaw message send --channel whatsapp --target <number> --message <text>

Called inside the running Docker container via `docker exec`.
"""

import logging
import subprocess
import time

from . import config
from .whatsapp import _split_into_parts

logger = logging.getLogger(__name__)

CONTAINER = "openclaw"
WHATSAPP_TARGET = config.WHATSAPP_TO_NUMBER.removeprefix("whatsapp:")


def _exec_send(part: str) -> None:
    cmd = [
        "docker", "exec", CONTAINER,
        "openclaw", "message", "send",
        "--channel", "whatsapp",
        "--target", WHATSAPP_TARGET,
        "--message", part,
    ]
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(
            f"openclaw send failed (exit {result.returncode}): {result.stderr.strip()}"
        )


def send_openclaw(brief: str) -> int:
    parts = _split_into_parts(brief)
    logger.info(
        "Sending via OpenClaw to %s — %d part(s), total %d chars.",
        WHATSAPP_TARGET, len(parts), len(brief),
    )
    for i, part in enumerate(parts, start=1):
        logger.info("Sending part %d/%d (%d chars)…", i, len(parts), len(part))
        _exec_send(part)
        if i < len(parts):
            time.sleep(1)
    return len(parts)
