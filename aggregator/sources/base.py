from __future__ import annotations

import html
import re

from bs4 import BeautifulSoup

from ..models import Job


class Source:
    """Базовый класс источника. fetch() возвращает сырые заказы."""

    type: str = ""

    def __init__(self, cfg: dict, settings: dict):
        self.cfg = cfg
        self.settings = settings
        self.id: str = cfg["id"]
        self.name: str = cfg.get("name", self.id)
        self.kind: str = cfg.get("kind", "order")
        self.currency: str | None = cfg.get("currency")
        self.timeout: float = settings.get("request_timeout", 20)

    @property
    def link(self) -> str:
        return self.cfg.get("link") or self.cfg.get("url", "")

    def fetch(self) -> list[Job]:  # pragma: no cover - переопределяется
        raise NotImplementedError

    def make_job(self, native_id: str, title: str, url: str, **kwargs) -> Job:
        return Job(
            source=self.id,
            source_name=self.name,
            native_id=str(native_id),
            title=clean_text(title)[:200] or "(без названия)",
            url=url,
            kind=kwargs.pop("kind", self.kind),
            **kwargs,
        )


_WS_RE = re.compile(r"[ \t ]+")
_NL_RE = re.compile(r"\n{3,}")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return _NL_RE.sub("\n\n", text).strip()


def html_to_text(markup: str | None) -> str:
    if not markup:
        return ""
    soup = BeautifulSoup(markup, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for block in soup.find_all(["p", "div", "li"]):
        block.insert_after("\n")
    return clean_text(soup.get_text())
