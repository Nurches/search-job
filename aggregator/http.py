from __future__ import annotations

import time

import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,kk;q=0.8,en;q=0.7",
        })
    return _session


def get(url: str, *, timeout: float = 20, retries: int = 2, **kwargs) -> requests.Response:
    return request("GET", url, timeout=timeout, retries=retries, **kwargs)


def request(method: str, url: str, *, timeout: float = 20, retries: int = 2, **kwargs) -> requests.Response:
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = session().request(method, url, timeout=timeout, **kwargs)
            if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    assert last_exc is not None
    raise last_exc
