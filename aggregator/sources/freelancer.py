"""Freelancer.com — публичный API активных проектов (без ключа)."""
from __future__ import annotations

from datetime import datetime, timezone

from .. import http
from ..models import Job, iso
from .base import Source, clean_text

API = "https://www.freelancer.com/api/projects/0.1/projects/active/"


class FreelancerSource(Source):
    type = "freelancer"

    def fetch(self) -> list[Job]:
        params = {
            "limit": self.cfg.get("limit", 100),
            "full_description": "true",
            "job_details": "true",
            "sort_field": "time_updated",
            "compact": "true",
        }
        if self.cfg.get("query"):
            params["query"] = self.cfg["query"]
        resp = http.get(API, params=params, timeout=self.timeout)
        return self.parse(resp.json())

    def parse(self, data: dict) -> list[Job]:
        result = data.get("result") or {}
        jobs: list[Job] = []
        for p in result.get("projects", []):
            budget = p.get("budget") or {}
            currency = (p.get("currency") or {}).get("code")
            value = budget.get("maximum") or budget.get("minimum")
            hourly = p.get("type") == "hourly"
            budget_text = None
            if value and currency:
                lo, hi = budget.get("minimum"), budget.get("maximum")
                rng = f"{lo:,.0f}–{hi:,.0f}" if lo and hi else f"{value:,.0f}"
                budget_text = f"{rng} {currency}" + ("/час" if hourly else "")
                if hourly:
                    value = value * 40  # грубая оценка: неделя работы
            skills = ", ".join(j.get("name", "") for j in p.get("jobs") or [] if j.get("name"))
            desc = clean_text(p.get("description") or p.get("preview_description") or "")
            if skills:
                desc = f"Навыки: {skills}\n{desc}"
            submitted = p.get("time_submitted") or p.get("time_updated")
            seo = p.get("seo_url")
            jobs.append(self.make_job(
                native_id=str(p.get("id")),
                title=p.get("title", ""),
                url=f"https://www.freelancer.com/projects/{seo}" if seo else f"https://www.freelancer.com/projects/{p.get('id')}",
                description=desc[:2500],
                published=iso(datetime.fromtimestamp(submitted, tz=timezone.utc)) if submitted else None,
                budget_value=float(value) if value else None,
                currency=currency if value else None,
                budget_text=budget_text,
                responses=(p.get("bid_stats") or {}).get("bid_count"),
            ))
        return jobs
