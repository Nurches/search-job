"""Главный цикл: собрать → отфильтровать → оценить → убрать дубли → сохранить."""
from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
from pathlib import Path

from . import classify
from .budget import extract_budget, format_budget, to_kzt
from .models import Job, iso, normalize_text, parse_iso, utcnow
from .sources import build_sources
from .sources.base import Source

log = logging.getLogger("aggregator")


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("не удалось прочитать %s: %s", path, exc)
        return {}


def fetch_all(sources: list[Source], workers: int = 8) -> tuple[list[tuple[Source, Job]], list[dict]]:
    results: list[tuple[Source, Job]] = []
    health: list[dict] = []

    def run(src: Source):
        return src, src.fetch()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run, s): s for s in sources}
        for fut in as_completed(futures):
            src = futures[fut]
            entry = {"id": src.id, "name": src.name, "type": src.type, "link": src.link,
                     "ok": False, "fetched": 0, "accepted": 0, "error": None}
            try:
                _, jobs = fut.result()
                entry["ok"] = True
                entry["fetched"] = len(jobs)
                entry["name"] = src.name
                results.extend((src, j) for j in jobs)
                log.info("%-28s %3d записей", src.id, len(jobs))
            except Exception as exc:  # noqa: BLE001 - один источник не должен ронять всё
                entry["error"] = f"{type(exc).__name__}: {exc}"[:300]
                log.warning("%-28s ОШИБКА %s", src.id, entry["error"])
            health.append(entry)
    health.sort(key=lambda h: (h["type"] == "telegram", h["name"].lower()))
    return results, health


def enrich_budget(job: Job, source_cfg: dict, rates: dict) -> None:
    if job.budget_value is None:
        found = extract_budget(job.text, default_currency=source_cfg.get("currency"))
        if found:
            job.budget_value, job.currency = found
            job.budget_text = format_budget(*found)
    job.budget_kzt = to_kzt(job.budget_value, job.currency, rates)


def _words(job: Job) -> set[str]:
    return set(normalize_text(job.text).split()[:120])


def dedupe(jobs: list[Job]) -> list[Job]:
    """Убирает дубли: одинаковый URL/отпечаток или очень похожий текст."""
    jobs = sorted(jobs, key=lambda j: j.first_seen or "")
    kept: list[Job] = []
    by_fp: dict[str, Job] = {}
    by_url: dict[str, Job] = {}
    word_sets: list[tuple[Job, set[str]]] = []
    for job in jobs:
        dup = by_url.get(job.url) or by_fp.get(job.fingerprint)
        if dup is None and job.source.startswith("tg:"):
            ws = _words(job)
            if len(ws) >= 8:
                for other, ows in word_sets[-600:]:
                    inter = len(ws & ows)
                    if inter and inter / len(ws | ows) >= 0.8:
                        dup = other
                        break
        if dup is not None:
            if dup.source != job.source and job.source_name not in dup.also_in:
                dup.also_in.append(job.source_name)
            continue
        kept.append(job)
        by_fp[job.fingerprint] = job
        if job.url:
            by_url[job.url] = job
        if job.source.startswith("tg:"):
            word_sets.append((job, _words(job)))
    return kept


def run(config: dict, out_path: Path, *, notify: bool = True, only: str | None = None) -> dict:
    settings = config.get("settings", {})
    rates = settings.get("rates_to_kzt", {"KZT": 1})
    thresholds = settings.get("thresholds", {"hot": 60, "warm": 35})
    retention = timedelta(days=settings.get("retention_days", 14))
    max_items = settings.get("max_items", 3000)
    now = utcnow()

    state = load_state(out_path)
    had_state = bool(state.get("jobs"))
    existing = {j["id"]: Job.from_dict(j) for j in state.get("jobs", [])}

    sources = build_sources(config)
    if only:
        rx = re.compile(only)
        sources = [s for s in sources if rx.search(s.id)]
    fetched, health = fetch_all(sources, workers=settings.get("workers", 8))
    health_by_id = {h["id"]: h for h in health}

    rejected: dict[str, int] = {}
    new_ids: list[str] = []
    for src, job in fetched:
        reason = classify.rejection_reason(job, src.cfg)
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        health_by_id[src.id]["accepted"] += 1
        old = existing.get(job.id)
        if old:
            job.first_seen = old.first_seen
            job.notified = old.notified
            job.also_in = old.also_in
        else:
            job.first_seen = iso(now)
            new_ids.append(job.id)
        enrich_budget(job, src.cfg, rates)
        existing[job.id] = job

    # Чистим старое, пересчитываем оценки (свежесть меняется со временем).
    cutoff = now - retention
    jobs = []
    for job in existing.values():
        ts = parse_iso(job.published) or parse_iso(job.first_seen) or now
        if ts < cutoff:
            continue
        classify.score(job, thresholds, now)
        jobs.append(job)
    jobs = dedupe(jobs)
    jobs.sort(key=lambda j: (parse_iso(j.published) or parse_iso(j.first_seen) or now), reverse=True)
    jobs = jobs[:max_items]

    kept_ids = {j.id for j in jobs}
    new_set = set(new_ids)
    fresh = [j for j in jobs if j.id in new_set]
    if notify and had_state:
        from .notify import notify_hot
        notify_hot([j for j in fresh if j.temperature == "hot" and not j.notified], settings)
    for j in fresh:
        # Первый прогон без истории: не рассылаем сотни старых заказов.
        if not had_state:
            j.notified = True

    # Если источник этого прогона упал, его старые заказы остаются — это нормально.
    prev_health = {h["id"]: h for h in state.get("sources", [])}
    for h in health:
        prev = prev_health.get(h["id"], {})
        h["last_ok"] = iso(now) if h["ok"] else prev.get("last_ok")

    stats = {
        "total": len(jobs),
        "hot": sum(j.temperature == "hot" for j in jobs),
        "warm": sum(j.temperature == "warm" for j in jobs),
        "cold": sum(j.temperature == "cold" for j in jobs),
        "new_this_run": len(new_set & kept_ids),
        "fetched_this_run": len(fetched),
        "rejected_this_run": rejected,
        "sources_ok": sum(h["ok"] for h in health),
        "sources_total": len(health),
    }
    output = {
        "generated_at": iso(now),
        "stats": stats,
        "thresholds": thresholds,
        "sources": health,
        "directory": config.get("directory", []),
        "jobs": [j.to_dict() for j in jobs],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, out_path)
    log.info("Итого: %d заказов (🔥%d 🟡%d ❄️%d), новых %d, отброшено %s",
             stats["total"], stats["hot"], stats["warm"], stats["cold"], stats["new_this_run"], rejected)
    return output
