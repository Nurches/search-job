"""Уведомления о горячих заказах в Telegram-бот.

Нужны переменные окружения (в GitHub — секреты репозитория):
  TELEGRAM_BOT_TOKEN — токен бота от @BotFather
  TELEGRAM_CHAT_ID   — ваш chat id (узнать: написать боту и открыть
                       https://api.telegram.org/bot<TOKEN>/getUpdates)
"""
from __future__ import annotations

import html
import logging
import os

from . import http
from .keywords import TAG_LABELS
from .models import Job

log = logging.getLogger("aggregator")


def format_message(job: Job) -> str:
    parts = [f"🔥 <b>{html.escape(job.title)}</b>"]
    meta = [html.escape(job.source_name)]
    if job.budget_text:
        meta.append(f"💰 {html.escape(job.budget_text)}")
    if job.responses is not None:
        meta.append(f"👥 {job.responses} откл.")
    meta.append(f"score {job.score}")
    parts.append(" · ".join(meta))
    if job.tags:
        parts.append(" ".join(f"#{TAG_LABELS.get(t, t).replace('/', '_').replace(' ', '_')}" for t in job.tags))
    desc = job.description.strip()
    if desc and desc != job.title:
        parts.append(html.escape(desc[:500] + ("…" if len(desc) > 500 else "")))
    parts.append(f'<a href="{html.escape(job.url)}">Открыть заказ →</a>')
    return "\n\n".join(parts)


def notify_hot(jobs: list[Job], settings: dict) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id or not jobs:
        return 0
    limit = settings.get("notify_limit", 10)
    jobs = sorted(jobs, key=lambda j: j.score, reverse=True)
    sent = 0
    for job in jobs[:limit]:
        try:
            http.request(
                "POST", f"https://api.telegram.org/bot{token}/sendMessage", retries=1,
                json={"chat_id": chat_id, "text": format_message(job), "parse_mode": "HTML",
                      "disable_web_page_preview": True},
            )
            job.notified = True
            sent += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("не удалось отправить уведомление: %s", type(exc).__name__)
    for job in jobs[limit:]:
        job.notified = True  # не копим хвост, чтобы не заспамить в следующий раз
    log.info("отправлено уведомлений: %d", sent)
    return sent
