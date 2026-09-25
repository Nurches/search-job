"""Извлечение бюджета из текста и перевод в тенге."""
from __future__ import annotations

import re

CURRENCY_ALIASES = {
    "KZT": [r"₸", r"тг\b", r"тенге", r"kzt"],
    "RUB": [r"₽", r"руб", r"р\.", r"\bр\b", r"rub"],
    "USD": [r"\$", r"usd", r"долл", r"dollar"],
    "EUR": [r"€", r"eur", r"евро"],
    "UAH": [r"грн", r"uah", r"₴"],
}

_CUR_PATTERN = "|".join(f"(?P<{code}>{'|'.join(p)})" for code, p in CURRENCY_ALIASES.items())
_NUM = r"\d[\d\s .,]*\d|\d"
_MULT = r"(?P<mult>млн|mln|тыс\.?|к\b|k\b)?"

# "50 000 руб", "50к тг", "до 1 500$", "$500", "от 300 000 ₸"
_AFTER_RE = re.compile(rf"(?P<num>{_NUM})\s*{_MULT}\s*(?:{_CUR_PATTERN})", re.IGNORECASE)
_BEFORE_RE = re.compile(rf"(?:(?P<USD>\$)|(?P<EUR>€))\s*(?P<num>{_NUM})\s*{_MULT}", re.IGNORECASE)
# "1500-3000$", "50-100к руб", "$1500-3000"
_RANGE_AFTER_RE = re.compile(rf"(?P<lo>{_NUM})\s*[-–—]\s*(?P<num>{_NUM})\s*{_MULT}\s*(?:{_CUR_PATTERN})", re.IGNORECASE)
_RANGE_BEFORE_RE = re.compile(rf"(?:(?P<USD>\$)|(?P<EUR>€))\s*(?P<lo>{_NUM})\s*[-–—]\s*\$?\s*(?P<num>{_NUM})\s*{_MULT}", re.IGNORECASE)
# "бюджет: 50000" без валюты
_BUDGET_RE = re.compile(rf"(?:бюджет|оплата|цена|стоимость|budget)\s*[:\-–—]?\s*(?:до|от|около|~)?\s*(?P<num>{_NUM})\s*{_MULT}", re.IGNORECASE)


def _to_number(raw: str, mult: str | None) -> float | None:
    raw = raw.replace(" ", " ").strip()
    # "1 500,50" / "1.500" / "1,500" — пробелы и разделители тысяч
    raw = re.sub(r"\s+", "", raw)
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", raw):
        raw = re.sub(r"[.,]", "", raw)
    else:
        raw = raw.replace(",", ".")
        if raw.count(".") > 1:
            raw = raw.replace(".", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    mult = (mult or "").lower().rstrip(".")
    if mult in ("к", "k", "тыс"):
        value *= 1_000
    elif mult in ("млн", "mln"):
        value *= 1_000_000
    return value


def _currency(match: re.Match) -> str | None:
    for code in CURRENCY_ALIASES:
        if match.groupdict().get(code):
            return code
    return None


def extract_budget(text: str, default_currency: str | None = None) -> tuple[float, str] | None:
    """Возвращает (сумма, валюта) — максимальную найденную сумму."""
    candidates: list[tuple[float, str]] = []
    for regex in (_RANGE_AFTER_RE, _RANGE_BEFORE_RE, _AFTER_RE, _BEFORE_RE):
        for m in regex.finditer(text):
            cur = _currency(m)
            value = _to_number(m.group("num"), m.groupdict().get("mult"))
            if cur and value and value >= 1:
                candidates.append((value, cur))
    if not candidates and default_currency:
        for m in _BUDGET_RE.finditer(text):
            value = _to_number(m.group("num"), m.group("mult"))
            if value and value >= 100:
                candidates.append((value, default_currency))
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[0] * _RATE_HINT.get(c[1], 1))


# Грубые курсы только для выбора максимума; реальные курсы — в config.yaml.
_RATE_HINT = {"KZT": 1, "RUB": 6, "USD": 500, "EUR": 550, "UAH": 12}


def to_kzt(value: float | None, currency: str | None, rates: dict[str, float]) -> int | None:
    if value is None or not currency:
        return None
    rate = rates.get(currency.upper())
    if rate is None:
        return None
    return int(round(value * rate))


def format_budget(value: float, currency: str) -> str:
    symbols = {"KZT": "₸", "RUB": "₽", "USD": "$", "EUR": "€", "UAH": "₴"}
    num = f"{value:,.0f}".replace(",", " ")
    sym = symbols.get(currency, currency)
    return f"${num}" if currency == "USD" else f"{num} {sym}"
