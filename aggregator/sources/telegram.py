"""Публичные Telegram-каналы через веб-превью https://t.me/s/<канал>.

Не требует API-ключей и аккаунта. Работает только для публичных каналов
(и публичных групп с включённым превью). Для закрытых чатов нужен Telethon.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .. import http
from ..models import Job, iso, parse_iso
from .base import Source, clean_text


class SourceError(Exception):
    pass


class TelegramChannel(Source):
    type = "telegram"

    def __init__(self, cfg: dict, settings: dict):
        channel = cfg["channel"].lstrip("@").strip()
        self._explicit_name = bool(cfg.get("name"))
        cfg = {"id": f"tg:{channel}", "name": cfg.get("name") or f"@{channel}", **cfg}
        cfg.setdefault("check_offer", True)
        cfg.setdefault("link", f"https://t.me/{channel}")
        super().__init__(cfg, settings)
        self.channel = channel

    def fetch(self) -> list[Job]:
        pages = int(self.cfg.get("pages", 1))
        jobs: list[Job] = []
        before: str | None = None
        for _ in range(max(1, pages)):
            url = f"https://t.me/s/{self.channel}" + (f"?before={before}" if before else "")
            resp = http.get(url, timeout=self.timeout)
            batch = self.parse(resp.text)
            if not self._raw_ids:
                if before is None:
                    raise SourceError("нет публичной ленты (канал не найден или закрыт)")
                break
            jobs.extend(batch)
            before = str(min(self._raw_ids))
        return jobs

    def parse(self, markup: str) -> list[Job]:
        soup = BeautifulSoup(markup, "lxml")
        title_el = soup.select_one(".tgme_channel_info_header_title")
        if title_el and not self._explicit_name:
            self.name = clean_text(title_el.get_text())
        jobs: list[Job] = []
        self._raw_ids: list[int] = []
        for msg in soup.select(".tgme_widget_message[data-post]"):
            post = msg.get("data-post", "")
            if "/" not in post:
                continue
            _, msg_id = post.rsplit("/", 1)
            if not msg_id.isdigit():
                continue
            self._raw_ids.append(int(msg_id))
            text_el = msg.select_one(".tgme_widget_message_text")
            if text_el is None:
                continue  # фото/стикер без подписи
            for br in text_el.find_all("br"):
                br.replace_with("\n")
            text = clean_text(text_el.get_text())
            if len(text) < 25:
                continue
            time_el = msg.select_one(".tgme_widget_message_date time[datetime]") or msg.select_one("time[datetime]")
            published = iso(parse_iso(time_el["datetime"])) if time_el else None
            first_line = next((ln for ln in text.splitlines() if ln.strip()), text)
            jobs.append(self.make_job(
                native_id=msg_id,
                title=first_line[:140],
                url=f"https://t.me/{post}",
                description=text[:2500],
                published=published,
            ))
        return jobs
