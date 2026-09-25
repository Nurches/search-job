"""Универсальный RSS/Atom-источник (Хабр Фриланс, FL.ru, Weblancer, Reddit, ...)."""
from __future__ import annotations

import calendar
import hashlib
import re
from datetime import datetime, timezone

import feedparser

from .. import http
from ..models import Job, iso
from .base import Source, clean_text, html_to_text


class RssSource(Source):
    type = "rss"

    def fetch(self) -> list[Job]:
        resp = http.get(self.cfg["url"], timeout=self.timeout)
        return self.parse(resp.content)

    def parse(self, content: bytes | str) -> list[Job]:
        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            raise ValueError(f"не удалось разобрать RSS: {feed.bozo_exception}")
        title_filter = self.cfg.get("title_filter")
        title_rx = re.compile(title_filter, re.IGNORECASE) if title_filter else None
        jobs: list[Job] = []
        for entry in feed.entries:
            title = clean_text(entry.get("title", ""))
            if title_rx and not title_rx.search(title):
                continue
            link = entry.get("link", "")
            raw_desc = entry.get("summary") or ""
            if entry.get("content"):
                raw_desc = entry["content"][0].get("value") or raw_desc
            description = html_to_text(raw_desc)[:2500]
            native_id = entry.get("id") or link or title
            native_id = _short_id(native_id)
            published = None
            for key in ("published_parsed", "updated_parsed"):
                if entry.get(key):
                    ts = calendar.timegm(entry[key])
                    published = iso(datetime.fromtimestamp(ts, tz=timezone.utc))
                    break
            jobs.append(self.make_job(
                native_id=native_id,
                title=title,
                url=link,
                description=description,
                published=published,
            ))
        return jobs


def _short_id(value: str) -> str:
    m = re.search(r"(\d{4,})(?!.*\d{4,})", value)
    if m:
        return m.group(1)
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
