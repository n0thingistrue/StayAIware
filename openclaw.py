"""
openclaw.py — Send the daily brief via OpenClaw (self-hosted WhatsApp gateway).

OpenClaw has no HTTP endpoint for outbound messages — it exposes a CLI:
    openclaw message send --channel whatsapp --target <number> --message <text>

We call that CLI inside the running Docker container via `docker exec`.
The message is split into parts ≤ 1550 chars (same rule as Twilio) so long
briefs arrive as sequential WhatsApp messages without cutting paragraphs.
"""

import logging
import subprocess
import time

import config
from whatsapp import _split_into_parts  # reuse the same splitting logic

logger = logging.getLogger(__name__)

# Name must match `container_name` in docker-compose.yml
CONTAINER = "openclaw"

# Target phone number — strip the "whatsapp:" prefix Twilio uses.
# e.g. "whatsapp:+33612345678" → "+33612345678"
_raw_to = config.WHATSAPP_TO_NUMBER
WHATSAPP_TARGET = _raw_to.removeprefix("whatsapp:")


def _exec_send(part: str) -> None:
    """
    Run `openclaw message send` inside the Docker container for one part.
    Raises RuntimeError if the command exits non-zero.
    """
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
    if result.stdout.strip():
        logger.debug("openclaw stdout: %s", result.stdout.strip())


def send_openclaw(brief: str) -> int:
    """
    Split the brief at section boundaries and send each part via OpenClaw.
    Returns the number of parts sent.
    Raises RuntimeError on failure.
    """
    parts = _split_into_parts(brief)
    logger.info(
        "Sending via OpenClaw to %s — %d part(s), total %d chars.",
        WHATSAPP_TARGET, len(parts), len(brief),
    )
    for i, part in enumerate(parts, start=1):
        logger.info("Sending part %d/%d (%d chars)…", i, len(parts), len(part))
        _exec_send(part)
        if i < len(parts):
            time.sleep(1)  # preserve message order
    return len(parts)
