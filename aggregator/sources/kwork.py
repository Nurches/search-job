"""Kwork — биржа проектов (раздел «Разработка и IT», c=11).

Kwork отдаёт список проектов JSON-ом на POST /projects (так работает их
собственный фронтенд), а в HTML страницы тот же список лежит в window.stateData.
Пробуем оба способа.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from .. import http
from ..models import Job, iso
from .base import Source, clean_text, html_to_text

MSK = timezone(timedelta(hours=3))


class KworkSource(Source):
    type = "kwork"

    def fetch(self) -> list[Job]:
        category = self.cfg.get("category", 11)
        pages = int(self.cfg.get("pages", 2))
        jobs: list[Job] = []
        for page in range(1, pages + 1):
            wants = self._fetch_page(category, page)
            if not wants:
                break
            jobs.extend(self.parse_wants(wants))
        if not jobs:
            raise ValueError("не найден список проектов (возможно, изменилась вёрстка Kwork)")
        return jobs

    def _fetch_page(self, category: int, page: int) -> list[dict]:
        url = "https://kwork.ru/projects"
        try:
            resp = http.request(
                "POST", url, timeout=self.timeout, retries=1,
                data={"c": category, "page": page},
                headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
            )
            data = resp.json()
            wants = _find_wants(data)
            if wants:
                return wants
        except Exception:  # noqa: BLE001 - падаем на HTML
            pass
        resp = http.get(url, params={"c": category, "page": page}, timeout=self.timeout)
        return extract_wants_from_html(resp.text)

    def parse_wants(self, wants: list[dict]) -> list[Job]:
        jobs: list[Job] = []
        for w in wants:
            wid = w.get("id") or w.get("want_id")
            if not wid:
                continue
            title = w.get("name") or w.get("title") or ""
            desc = w.get("description") or w.get("desc") or ""
            desc = html_to_text(desc) if "<" in desc else clean_text(desc)
            price = _to_float(w.get("priceLimit") or w.get("price_limit") or w.get("price"))
            max_price = _to_float(w.get("possiblePriceLimit") or w.get("possible_price_limit"))
            budget = max(filter(None, [price, max_price]), default=None)
            budget_text = None
            if price:
                budget_text = f"до {price:,.0f} ₽".replace(",", " ")
                if max_price and max_price > price:
                    budget_text = f"{budget_text} (допустимо до {max_price:,.0f} ₽)".replace(",", " ")
            responses = w.get("kwork_count") or w.get("offers_count") or w.get("offers")
            jobs.append(self.make_job(
                native_id=str(wid),
                title=title,
                url=f"https://kwork.ru/projects/{wid}",
                description=desc[:2500],
                published=_parse_date(w.get("date_create") or w.get("date_active") or w.get("dateCreate")),
                budget_value=budget,
                currency="RUB" if budget else None,
                budget_text=budget_text,
                responses=int(responses) if str(responses or "").isdigit() else None,
            ))
        return jobs


def _find_wants(data) -> list[dict] | None:
    if isinstance(data, dict):
        for key in ("wants", "projects"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
            if isinstance(val, dict) and isinstance(val.get("data"), list):
                return val["data"]
        for val in data.values():
            found = _find_wants(val)
            if found:
                return found
    elif isinstance(data, list):
        for val in data:
            found = _find_wants(val)
            if found:
                return found
    return None


def extract_wants_from_html(markup: str) -> list[dict]:
    decoder = json.JSONDecoder()
    m = re.search(r"window\.stateData\s*=\s*", markup)
    if m:
        try:
            state, _ = decoder.raw_decode(markup, m.end())
            found = _find_wants(state)
            if found:
                return found
        except ValueError:
            pass
    for m in re.finditer(r'"wants"\s*:\s*(?=\[)', markup):
        try:
            wants, _ = decoder.raw_decode(markup, m.end())
        except ValueError:
            continue
        if isinstance(wants, list) and wants and isinstance(wants[0], dict):
            return wants
    return []


def _to_float(value) -> float | None:
    try:
        v = float(str(value).replace(" ", "")) if value not in (None, "") else None
    except ValueError:
        return None
    return v if v and v > 0 else None


def _parse_date(value) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)) or str(value).isdigit():
        return iso(datetime.fromtimestamp(int(value), tz=timezone.utc))
    try:
        dt = datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=MSK)
    except ValueError:
        return None
    return iso(dt)
