from pathlib import Path

from aggregator.sources.freelancer import FreelancerSource
from aggregator.sources.hh import HeadHunterSource
from aggregator.sources.kwork import KworkSource, extract_wants_from_html
from aggregator.sources.rss import RssSource
from aggregator.sources.telegram import TelegramChannel

FIX = Path(__file__).parent / "fixtures"


def test_telegram_parse():
    src = TelegramChannel({"channel": "@freelance_kz"}, {})
    jobs = src.parse((FIX / "telegram.html").read_text(encoding="utf-8"))
    assert src.id == "tg:freelance_kz"
    assert src.name == "Фриланс Заказы KZ"
    assert [j.native_id for j in jobs] == ["101", "102", "103"]  # фото без подписи пропущено
    first = jobs[0]
    assert first.title == "#заказ Нужен Flutter разработчик"
    assert first.url == "https://t.me/freelance_kz/101"
    assert first.published == "2026-09-25T10:00:00Z"
    assert "Бюджет 500 000 тг" in first.description
    assert src._raw_ids == [101, 102, 103, 104]


def test_rss_parse():
    src = RssSource({"id": "habr", "name": "Хабр", "url": "x"}, {})
    jobs = src.parse((FIX / "habr.rss").read_bytes())
    assert len(jobs) == 2
    assert jobs[0].native_id == "555111"
    assert jobs[0].published == "2026-09-25T06:30:00Z"
    assert "Бюджет: 30 000 руб" in jobs[0].description


def test_rss_title_filter():
    src = RssSource({"id": "r", "url": "x", "title_filter": "aiogram"}, {})
    jobs = src.parse((FIX / "habr.rss").read_bytes())
    assert [j.native_id for j in jobs] == ["555111"]


def test_kwork_from_html():
    wants = extract_wants_from_html((FIX / "kwork.html").read_text(encoding="utf-8"))
    src = KworkSource({"id": "kwork", "name": "Kwork"}, {})
    jobs = src.parse_wants(wants)
    assert len(jobs) == 1
    j = jobs[0]
    assert j.url == "https://kwork.ru/projects/2451001"
    assert j.budget_value == 45000 and j.currency == "RUB"
    assert j.responses == 3
    assert j.published == "2026-09-25T09:00:00Z"  # МСК -> UTC


def test_hh_parse():
    data = {"items": [{
        "id": "987", "name": "Flutter-разработчик", "alternate_url": "https://hh.kz/vacancy/987",
        "published_at": "2026-09-25T10:00:00+0500",
        "salary": {"from": 600000, "to": 900000, "currency": "KZT"},
        "snippet": {"requirement": "Опыт с <highlighttext>Flutter</highlighttext> от 2 лет", "responsibility": None},
        "employer": {"name": "ТОО Альфа"}, "area": {"name": "Алматы"},
        "schedule": {"name": "Удаленная работа"}, "employment": {"name": "Проектная работа"},
    }]}
    src = HeadHunterSource({"id": "hh", "name": "hh"}, {})
    j = src.parse(data)[0]
    assert j.kind == "order"
    assert j.published == "2026-09-25T05:00:00Z"
    assert j.budget_value == 900000 and j.currency == "KZT"
    assert "Flutter от 2 лет" in j.description


def test_freelancer_parse():
    data = {"result": {"projects": [{
        "id": 42, "title": "Build Flutter app", "seo_url": "mobile/build-flutter-app",
        "description": "Need an app", "time_submitted": 1790000000, "type": "fixed",
        "budget": {"minimum": 250, "maximum": 750}, "currency": {"code": "USD"},
        "bid_stats": {"bid_count": 12}, "jobs": [{"name": "Flutter"}, {"name": "Mobile App Development"}],
    }]}}
    src = FreelancerSource({"id": "fr", "name": "Freelancer"}, {})
    j = src.parse(data)[0]
    assert j.url == "https://www.freelancer.com/projects/mobile/build-flutter-app"
    assert j.budget_value == 750 and j.responses == 12
    assert j.description.startswith("Навыки: Flutter")
