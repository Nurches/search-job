from datetime import timedelta

import pytest

from aggregator import classify
from aggregator.budget import extract_budget, to_kzt
from aggregator.models import Job, iso, utcnow

TG = {"check_offer": True}
TH = {"hot": 60, "warm": 35}


def job(text, source="tg:test", **kw):
    title, _, desc = text.partition("\n")
    return Job(source=source, source_name="t", native_id="1", title=title, url="u", description=text, **kw)


@pytest.mark.parametrize("text,reason", [
    ("Нужен разработчик Telegram-бота на aiogram, бюджет 50к руб", None),
    ("Ищу Flutter разработчика для приложения доставки", None),
    ("Требуется верстальщик лендинга на Tilda", None),
    ("Выполню любые задачи по Python и Django недорого, портфолио в профиле", "offer"),
    ("Ищу работу frontend разработчиком, React, 3 года опыта", "offer"),
    ("#резюме Python backend developer, FastAPI, Django", "offer"),
    ("Заработок от 5000 руб в день без вложений, пиши", "spam"),
    ("Нужен копирайтер для статей о путешествиях, оплата 500 руб", "not_it"),
    ("Нужен монтажёр видео для reels", "not_it"),
    ("Всем привет! Кто сегодня идёт на митап по React?", "no_order_marker"),
])
def test_rejection_telegram(text, reason):
    assert classify.rejection_reason(job(text), TG) == reason


def test_platform_sources_skip_offer_check():
    # на биржах всё — заказы, проверка «реклама исполнителя» не нужна
    assert classify.rejection_reason(job("Сделать сайт на WordPress", source="flru"), {}) is None


def test_it_only_source_accepts_without_keywords():
    assert classify.rejection_reason(job("Доработка проекта", source="kwork"), {"it_only": True}) is None


def test_tags():
    tags = classify.detect_tags("Мобильное приложение на Flutter, бэкенд на FastAPI, админ-панель на React")
    assert {"mobile", "backend", "frontend", "web"} <= set(tags)


def test_long_term_is_not_urgent():
    j = job("Нужен React разработчик\nДолгосрочное сотрудничество", published=iso(utcnow()))
    classify.score(j, TH)
    assert "срочно" not in j.reasons


def test_hot_vs_cold():
    now = utcnow()
    hot = job("Нужно мобильное приложение под ключ на Flutter + FastAPI\niOS и Android, бюджет 800 000 тг, Алматы, @client",
              published=iso(now - timedelta(minutes=30)), budget_kzt=800_000, responses=1)
    classify.score(hot, TH, now)
    assert hot.temperature == "hot", hot.reasons

    cold = job("Поправить цвет кнопки на сайте WordPress\nмелкие правки",
               source="flru", published=iso(now - timedelta(days=5)), budget_kzt=5_000, responses=30)
    classify.score(cold, TH, now)
    assert cold.temperature == "cold", (cold.score, cold.reasons)


@pytest.mark.parametrize("text,expected", [
    ("Бюджет 150 000 ₽", (150000, "RUB")),
    ("оплата 50к тг", (50000, "KZT")),
    ("$1500-3000 fixed", (3000, "USD")),
    ("от 300 000 до 500 000 тенге", (500000, "KZT")),
    ("бюджет: 20000", (20000, "RUB")),
    ("в 2026 году запускаем 3 проекта", None),
])
def test_budget(text, expected):
    got = extract_budget(text, default_currency="RUB")
    assert (got if got is None else (int(got[0]), got[1])) == expected


def test_to_kzt():
    assert to_kzt(1000, "RUB", {"RUB": 6.3}) == 6300
    assert to_kzt(1000, "XXX", {"RUB": 6.3}) is None
