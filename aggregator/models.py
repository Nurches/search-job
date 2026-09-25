"""Модель заказа, общая для всех источников."""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


_URL_RE = re.compile(r"https?://\S+|t\.me/\S+|@\w+")
_NON_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)


def normalize_text(text: str) -> str:
    text = _URL_RE.sub(" ", text.lower())
    text = text.replace("ё", "е")
    return _NON_WORD_RE.sub(" ", text).strip()


@dataclass
class Job:
    source: str                      # id источника (habr, kwork, tg:channel...)
    source_name: str                 # человекочитаемое имя
    native_id: str                   # id внутри источника
    title: str
    url: str
    description: str = ""
    published: str | None = None     # ISO UTC
    kind: str = "order"              # order | vacancy
    budget_text: str | None = None
    budget_value: float | None = None
    currency: str | None = None
    budget_kzt: int | None = None
    responses: int | None = None
    location: str | None = None
    # заполняются пайплайном
    first_seen: str | None = None
    tags: list[str] = field(default_factory=list)
    score: int = 0
    temperature: str = "cold"        # hot | warm | cold
    reasons: list[str] = field(default_factory=list)
    also_in: list[str] = field(default_factory=list)
    notified: bool = False

    @property
    def id(self) -> str:
        return f"{self.source}:{self.native_id}"

    @property
    def fingerprint(self) -> str:
        base = normalize_text(f"{self.title} {self.description}")[:240]
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

    @property
    def text(self) -> str:
        return f"{self.title}\n{self.description}"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["id"] = self.id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
