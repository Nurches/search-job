"""Демо-данные, чтобы посмотреть сайт без доступа к источникам."""
from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from . import classify
from .models import Job, iso, utcnow
from .pipeline import enrich_budget

SAMPLES = [
    ("kwork", "Kwork", "Мобильное приложение на Flutter для службы доставки", "Нужно приложение под ключ для iOS и Android: каталог, корзина, оплата, личный кабинет курьера. Бэкенд на FastAPI или Go. Бюджет до 150 000 ₽.", 1, 2),
    ("tg:freelancetaverna", "Фриланс Таверна", "Ищу разработчика Telegram-бота для записи клиентов", "Ищу разработчика Telegram-бота для записи клиентов в салон, Алматы. Интеграция с Google таблицами. Бюджет 120 000 тг. Пишите @salon_owner", 0.5, None),
    ("habr", "Хабр Фриланс", "Разработка MVP маркетплейса на React + Django", "Стартап ищет full-stack разработчика: React фронтенд, Django REST API, PostgreSQL, админ-панель. Долгосрочное сотрудничество.", 5, 4),
    ("flru", "FL.ru", "Поправить вёрстку на лендинге", "Небольшие правки на сайте WordPress, поменять цвет кнопок. 3000 руб.", 2, 18),
    ("hh-kz", "hh.kz — IT в Казахстане", "Golang разработчик (удалённо)", "ТОО Технолоджи · Астана · Удаленная работа\nРазработка микросервисов на Go, PostgreSQL, Kafka. от 800 000 до 1 200 000 KZT", 20, None),
    ("freelancer", "Freelancer.com", "Build a React Native app for fitness tracking", "Skills: Mobile App Development, React Native, Node.js\nNeed a developer to build a cross-platform fitness app with backend API. Budget $1500-3000", 8, 25),
    ("tg:remowork", "Remote Work", "Нужен фронтенд на Vue для админки", "#вакансия Нужен фронтенд разработчик Vue 3 на проект, админка CRM, оплата 2000$ в месяц, удаленно", 30, None),
    ("kwork", "Kwork", "Парсер товаров с Wildberries в Google Sheets", "Написать парсер на Python, выгрузка в Google таблицы раз в сутки. до 8 000 ₽", 3, 11),
    ("tg:distantsiya", "Дистанция", "Курсовая работа по Java — нужна помощь", "Нужна курсовая работа по Java, ООП, до пятницы. Оплата 15 000 тг", 12, None),
    ("habr", "Хабр Фриланс", "Интеграция amoCRM с сайтом на Tilda", "Настроить передачу заявок с Tilda в amoCRM через API, бюджет 20 000 руб, срочно", 1.5, 1),
    ("flru", "FL.ru", "Дизайн интерфейса мобильного приложения в Figma", "UI/UX дизайн 25 экранов, прототип. Бюджет 40 000 руб", 40, 9),
    ("reddit-forhire", "Reddit r/forhire", "[Hiring] Flutter developer for a MVP (remote)", "Looking for a Flutter developer to build MVP with Firebase backend. $2000 fixed.", 6, None),
]


def write_demo(config: dict, out: Path) -> None:
    settings = config.get("settings", {})
    rates = settings.get("rates_to_kzt", {"KZT": 1})
    thresholds = settings.get("thresholds", {"hot": 60, "warm": 35})
    now = utcnow()
    jobs = []
    for i, (src, name, title, desc, hours_ago, responses) in enumerate(SAMPLES):
        ts = iso(now - timedelta(hours=hours_ago))
        job = Job(source=src, source_name=name, native_id=str(1000 + i), title=title,
                  url="https://example.com/demo", description=desc, published=ts,
                  first_seen=ts, responses=responses,
                  kind="vacancy" if src in ("hh-kz",) or "#вакансия" in desc else "order")
        enrich_budget(job, {"currency": "RUB"}, rates)
        classify.score(job, thresholds, now)
        jobs.append(job)
    jobs.sort(key=lambda j: j.published or "", reverse=True)
    sources = [{"id": s["id"], "name": s["name"], "type": s["type"], "link": s.get("link", ""), "ok": True,
                "fetched": 0, "accepted": 0, "error": None, "last_ok": iso(now)} for s in config.get("sources", [])]
    output = {
        "demo": True,
        "generated_at": iso(now),
        "stats": {"total": len(jobs), "hot": sum(j.temperature == "hot" for j in jobs),
                  "warm": sum(j.temperature == "warm" for j in jobs),
                  "cold": sum(j.temperature == "cold" for j in jobs),
                  "sources_ok": len(sources), "sources_total": len(sources)},
        "thresholds": thresholds,
        "sources": sources,
        "directory": config.get("directory", []),
        "jobs": [j.to_dict() for j in jobs],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=1), encoding="utf-8")
