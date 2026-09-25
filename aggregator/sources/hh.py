"""HeadHunter (hh.kz / hh.ru) через официальный API api.hh.ru.

Ищет IT-вакансии и проектную работу. area=40 — Казахстан.
Если hh начнёт требовать токен, задайте секрет HH_TOKEN (токен приложения).
"""
from __future__ import annotations

import os

from .. import http
from ..models import Job, iso, parse_iso
from .base import Source, clean_text, html_to_text

API = "https://api.hh.ru/vacancies"


class HeadHunterSource(Source):
    type = "hh"

    def fetch(self) -> list[Job]:
        params = {
            "per_page": 100,
            "order_by": "publication_time",
            "period": self.cfg.get("period_days", 3),
            **self.cfg.get("params", {}),
        }
        headers = {"HH-User-Agent": "search-job-aggregator/1.0 (github.com)"}
        token = os.environ.get("HH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = http.get(API, params=params, headers=headers, timeout=self.timeout)
        return self.parse(resp.json())

    def parse(self, data: dict) -> list[Job]:
        jobs: list[Job] = []
        for item in data.get("items", []):
            snippet = item.get("snippet") or {}
            parts = [snippet.get("responsibility"), snippet.get("requirement")]
            desc = "\n".join(html_to_text(p) for p in parts if p)
            employer = (item.get("employer") or {}).get("name")
            area = (item.get("area") or {}).get("name")
            schedule = (item.get("schedule") or {}).get("name")
            employment = (item.get("employment") or {}).get("name")
            meta = " · ".join(filter(None, [employer, area, schedule, employment]))
            if meta:
                desc = f"{meta}\n{desc}"
            salary = item.get("salary") or {}
            value = salary.get("to") or salary.get("from")
            currency = {"RUR": "RUB", "KZT": "KZT", "USD": "USD", "EUR": "EUR"}.get(salary.get("currency") or "", None)
            budget_text = None
            if value and currency:
                lo, hi = salary.get("from"), salary.get("to")
                rng = f"{lo:,}–{hi:,}" if lo and hi else (f"от {lo:,}" if lo else f"до {hi:,}")
                budget_text = f"{rng} {currency}/мес".replace(",", " ")
            is_project = "проект" in (employment or "").lower()
            published = item.get("published_at")
            if published and len(published) > 5 and published[-5] in "+-":
                published = published[:-2] + ":" + published[-2:]  # +0300 -> +03:00
            jobs.append(self.make_job(
                native_id=str(item.get("id")),
                title=clean_text(item.get("name", "")),
                url=item.get("alternate_url") or f"https://hh.kz/vacancy/{item.get('id')}",
                description=desc[:2500],
                published=iso(parse_iso(published)),
                kind="order" if is_project else "vacancy",
                budget_value=float(value) if value and currency else None,
                currency=currency if value else None,
                budget_text=budget_text,
                location=" ".join(filter(None, [area, schedule, "project" if is_project else None])),
            ))
        return jobs
