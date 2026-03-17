"""
feeds.py — Fetch and parse RSS feeds, return a clean list of articles.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

import config

logger = logging.getLogger(__name__)

# feedparser uses urllib internally; set a browser-like user-agent so feeds
# that block bots still respond.
feedparser.USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 daily-global-brief/1.0"
)


@dataclass
class Article:
    title: str
    description: str
    category: str
    source: str
    published: Optional[str] = None

    def to_text(self) -> str:
        parts = [f"[{self.category.upper()}] {self.source}: {self.title}"]
        if self.description:
            parts.append(self.description)
        return "\n".join(parts)


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    clean = re.sub(r"<[^>]+>", "", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _fetch_feed(url: str, source: str, category: str, max_items: int) -> list[Article]:
    """Parse a single RSS/Atom feed and return up to max_items articles."""
    try:
        # Some feeds redirect; requests follows redirects better than feedparser.
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
        # Truncate long descriptions
        if len(description) > 300:
            description = description[:297] + "..."

        published = None
        if hasattr(entry, "published"):
            published = entry.published

        articles.append(
            Article(
                title=title,
                description=description,
                category=category,
                source=source,
                published=published,
            )
        )

    logger.info("Fetched %d articles from %s", len(articles), source)
    return articles


def fetch_all_articles() -> list[Article]:
    """
    Load feeds from feeds_config.json, fetch every feed, deduplicate by title,
    then return a balanced selection across categories capped at max_total_articles.

    Balancing works by round-robin across categories so that even if geopolitics
    has many more sources than crypto or positive news, every category gets
    proportional representation in the final list.
    """
    with open(config.FEEDS_CONFIG_PATH, encoding="utf-8") as fh:
        cfg = json.load(fh)

    max_per_feed: int = cfg.get("max_articles_per_feed", 5)
    max_total: int = cfg.get("max_total_articles", 35)

    # Collect all articles, grouped by category, with deduplication.
    by_category: dict[str, list[Article]] = {}
    seen_titles: set[str] = set()

    for feed_def in cfg["feeds"]:
        cat = feed_def["category"]
        articles = _fetch_feed(
            url=feed_def["url"],
            source=feed_def["name"],
            category=cat,
            max_items=max_per_feed,
        )
        for article in articles:
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

    # Round-robin across categories so every category appears in the output.
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
            break  # All buckets exhausted

    logger.info("Returning %d balanced articles.", len(balanced))
    return balanced


def articles_to_prompt_text(articles: list[Article]) -> str:
    """Format all articles as a numbered list for the AI prompt."""
    lines = []
    for i, article in enumerate(articles, start=1):
        lines.append(f"{i}. {article.to_text()}")
    return "\n\n".join(lines)
