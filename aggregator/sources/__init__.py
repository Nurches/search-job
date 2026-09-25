from __future__ import annotations

import os

from .base import Source
from .freelancer import FreelancerSource
from .hh import HeadHunterSource
from .kwork import KworkSource
from .rss import RssSource
from .telegram import TelegramChannel

SOURCE_TYPES: dict[str, type[Source]] = {
    "rss": RssSource,
    "kwork": KworkSource,
    "hh": HeadHunterSource,
    "freelancer": FreelancerSource,
    "telegram": TelegramChannel,
}


def build_sources(config: dict) -> list[Source]:
    settings = config.get("settings", {})
    sources: list[Source] = []
    for cfg in config.get("sources", []):
        if cfg.get("enabled", True) is False:
            continue
        if cfg.get("requires_env") and not os.environ.get(cfg["requires_env"]):
            continue
        cls = SOURCE_TYPES[cfg["type"]]
        sources.append(cls(cfg, settings))
    tg = config.get("telegram", {})
    tg_defaults = {k: v for k, v in tg.items() if k != "channels"}
    for ch in tg.get("channels", []):
        cfg = {"channel": ch} if isinstance(ch, str) else dict(ch)
        if cfg.get("enabled", True) is False:
            continue
        sources.append(TelegramChannel({**tg_defaults, **cfg}, settings))
    return sources
