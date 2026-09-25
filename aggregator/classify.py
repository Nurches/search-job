"""Фильтрация и оценка заказов: IT или нет, горячий / тёплый / холодный."""
from __future__ import annotations

import re
from datetime import datetime

from . import keywords as kw
from .models import Job, parse_iso, utcnow


def _compile(patterns: list[str]) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in patterns), re.IGNORECASE | re.MULTILINE)


CATEGORY_RE = {tag: _compile(p) for tag, p in kw.CATEGORIES.items()}
ORDER_RE = _compile(kw.ORDER_MARKERS)
OFFER_RE = _compile(kw.OFFER_MARKERS)
SPAM_RE = _compile(kw.SPAM_MARKERS)
NON_IT_RE = _compile(kw.NON_IT_MARKERS)
BIG_RE = _compile(kw.BIG_PROJECT_MARKERS)
SMALL_RE = _compile(kw.SMALL_TASK_MARKERS)
URGENT_RE = _compile(kw.URGENT_MARKERS)
KZ_RE = _compile(kw.KZ_MARKERS)
CONTACT_RE = _compile(kw.CONTACT_MARKERS)
REMOTE_RE = _compile(kw.REMOTE_MARKERS)


def prepare(text: str) -> str:
    return text.lower().replace("ё", "е")


def detect_tags(text: str) -> list[str]:
    t = prepare(text)
    return [tag for tag, rx in CATEGORY_RE.items() if rx.search(t)]


def rejection_reason(job: Job, source_cfg: dict) -> str | None:
    """Причина отбросить заказ или None, если заказ подходит."""
    t = prepare(job.text)
    if SPAM_RE.search(t):
        return "spam"
    tags = detect_tags(job.text)
    it_only = source_cfg.get("it_only", False)
    if not tags and not it_only:
        return "not_it"
    if not tags and NON_IT_RE.search(t):
        return "not_it"
    if source_cfg.get("check_offer", False):
        # Чаты/каналы: отсекаем рекламу исполнителей и требуем признак заказа.
        head = prepare(job.description[:400] or job.title)
        if OFFER_RE.search(head) and not re.search(r"\bнуж(ен|на|но)\b|требуется|бюджет", head):
            return "offer"
        if not ORDER_RE.search(t):
            return "no_order_marker"
    return None


def _freshness(published: datetime | None, now: datetime) -> tuple[int, str | None]:
    if published is None:
        return 5, None
    hours = (now - published).total_seconds() / 3600
    if hours <= 3:
        return 30, "свежий (< 3 ч)"
    if hours <= 12:
        return 22, "сегодня"
    if hours <= 24:
        return 15, "за сутки"
    if hours <= 72:
        return 7, None
    return 0, "старый"


def _budget_points(kzt: int | None) -> tuple[int, str | None]:
    if kzt is None:
        return 0, None
    if kzt < 25_000:
        return 2, "маленький бюджет"
    if kzt < 100_000:
        return 8, None
    if kzt < 300_000:
        return 15, "хороший бюджет"
    if kzt < 1_000_000:
        return 22, "крупный бюджет"
    return 28, "очень крупный бюджет"


def score(job: Job, thresholds: dict, now: datetime | None = None) -> None:
    """Считает score/temperature/reasons/tags. Меняет job на месте."""
    now = now or utcnow()
    t = prepare(job.text)
    reasons: list[str] = []
    points = 0

    tags = detect_tags(job.text)
    job.tags = tags

    p, why = _freshness(parse_iso(job.published) or parse_iso(job.first_seen), now)
    points += p
    if why:
        reasons.append(why)

    p, why = _budget_points(job.budget_kzt)
    points += p
    if why:
        reasons.append(why)

    core = [tg for tg in tags if tg in kw.CORE_TAGS]
    if core:
        points += 8
        if "backend" in tags and ({"frontend", "mobile"} & set(tags)):
            points += 4
            reasons.append("фронт + бэк")

    big = len(set(m.group(0) for m in BIG_RE.finditer(t)))
    if big:
        points += min(15, 8 * big)
        reasons.append("проект под ключ / крупный")

    if SMALL_RE.search(t):
        points -= 8
        reasons.append("мелкая правка")

    if URGENT_RE.search(t):
        points += 5
        reasons.append("срочно")

    if job.kind == "order":
        points += 8
    elif REMOTE_RE.search(t) or "project" in (job.location or ""):
        points += 3

    if job.responses is not None:
        if job.responses <= 2:
            points += 10
            reasons.append("мало откликов")
        elif job.responses <= 7:
            points += 5
        elif job.responses > 15:
            points -= 8
            reasons.append("много откликов")

    if KZ_RE.search(t) or (job.location and KZ_RE.search(prepare(job.location))):
        points += 6
        reasons.append("Казахстан")

    if job.source.startswith("tg:") and CONTACT_RE.search(t):
        points += 4
        reasons.append("есть контакт")

    if "design" in tags and not core:
        points -= 5
    if "study" in tags:
        reasons.append("учебный заказ")

    job.score = max(0, min(100, points))
    if job.score >= thresholds.get("hot", 60):
        job.temperature = "hot"
    elif job.score >= thresholds.get("warm", 35):
        job.temperature = "warm"
    else:
        job.temperature = "cold"
    job.reasons = reasons
