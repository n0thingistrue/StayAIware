"""
feeds.py — Fetch and parse RSS feeds, return a clean list of articles.
"""

import calendar
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import feedparser
import requests

from . import config

logger = logging.getLogger(__name__)

feedparser.USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 stayaiware/1.0"
)


@dataclass
class Article:
    title: str
    description: str
    category: str
    source: str
    published: Optional[str] = None
    published_dt: Optional[datetime] = None

    def to_text(self) -> str:
        parts = [f"[{self.category.upper()}] {self.source}: {self.title}"]
        if self.description:
            parts.append(self.description)
        return "\n".join(parts)


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _fetch_feed(url: str, source: str, category: str, max_items: int) -> list[Article]:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": feedparser.USER_AGENT})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as exc:
        logger.warning("Could not fetch %s (%s): %s", source, url, exc)
        return []

    articles = []
    for entry in feed.entries[:max_items]:
        title = _strip_html(entry.get("title", "")).strip()
        if not title:
            continue

        description = _strip_html(
            entry.get("summary", "") or entry.get("description", "")
        )
        if len(description) > 300:
            description = description[:297] + "..."

        published = None
        published_dt = None
        if entry.get("published_parsed"):
            try:
                published = entry.published
                ts = calendar.timegm(entry.published_parsed)
                published_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            except Exception:
                pass

        articles.append(
            Article(
                title=title,
                description=description,
                category=category,
                source=source,
                published=published,
                published_dt=published_dt,
            )
        )

    logger.info("Fetched %d articles from %s", len(articles), source)
    return articles


def fetch_all_articles() -> list[Article]:
    with open(config.FEEDS_CONFIG_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)

    max_per_feed: int = cfg.get("max_articles_per_feed", 5)
    max_total: int = cfg.get("max_total_articles", 35)

    by_category: dict[str, list[Article]] = {}
    seen_titles: set[str] = set()

    active = set(cfg.get("active_categories", []))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    for feed_def in cfg["feeds"]:
        cat = feed_def["category"]
        if active and cat not in active:
            continue
        articles = _fetch_feed(
            url=feed_def["url"],
            source=feed_def["name"],
            category=cat,
            max_items=max_per_feed,
        )
        for article in articles:
            if article.published_dt and article.published_dt < cutoff:
                logger.debug("Skipping article older than 24h: %s", article.title[:50])
                continue
            key = article.title[:60].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                by_category.setdefault(cat, []).append(article)

    total_unique = sum(len(v) for v in by_category.values())
    logger.info(
        "Unique articles by category: %s (total %d, cap %d)",
        {k: len(v) for k, v in by_category.items()},
        total_unique,
        max_total,
    )

    balanced: list[Article] = []
    buckets = list(by_category.values())
    positions = [0] * len(buckets)

    while len(balanced) < max_total:
        added_this_round = 0
        for i, bucket in enumerate(buckets):
            if len(balanced) >= max_total:
                break
            if positions[i] < len(bucket):
                balanced.append(bucket[positions[i]])
                positions[i] += 1
                added_this_round += 1
        if added_this_round == 0:
            break

    logger.info("Returning %d balanced articles.", len(balanced))
    return balanced


def articles_to_prompt_text(articles: list[Article]) -> str:
    lines = []
    for i, article in enumerate(articles, start=1):
        lines.append(f"{i}. {article.to_text()}")
    return "\n\n".join(lines)
