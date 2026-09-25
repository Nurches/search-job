import json
from pathlib import Path

from aggregator import pipeline
from aggregator.sources.telegram import TelegramChannel

FIX = Path(__file__).parent / "fixtures"

CONFIG = {
    "settings": {"rates_to_kzt": {"KZT": 1, "RUB": 6.3}, "thresholds": {"hot": 60, "warm": 35}, "retention_days": 3650},
    "telegram": {"channels": ["freelance_kz", "freelance_dup"]},
    "directory": [{"name": "X", "url": "https://x", "region": "Мир", "auto": False}],
}


def fake_fetch(self):
    jobs = self.parse((FIX / "telegram.html").read_text(encoding="utf-8"))
    for j in jobs:  # второй канал репостит те же сообщения
        j.url = f"https://t.me/{self.channel}/{j.native_id}"
    return jobs


def test_run_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(TelegramChannel, "fetch", fake_fetch)
    out = tmp_path / "jobs.json"

    result = pipeline.run(CONFIG, out, notify=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data == json.loads(json.dumps(result))
    # из 3 сообщений в каждом канале остаётся 1 заказ (реклама и спам отброшены), дубль склеен
    assert len(data["jobs"]) == 1
    job = data["jobs"][0]
    assert job["budget_kzt"] == 500000
    assert job["tags"][:1] == ["mobile"]
    assert job["also_in"] == ["Фриланс Заказы KZ"]
    assert data["stats"]["rejected_this_run"] == {"offer": 2, "spam": 2}
    assert all(s["ok"] for s in data["sources"])
    first_seen = job["first_seen"]

    # Повторный прогон сохраняет first_seen и не плодит дубли
    pipeline.run(CONFIG, out, notify=False)
    data2 = json.loads(out.read_text(encoding="utf-8"))
    assert len(data2["jobs"]) == 1
    assert data2["jobs"][0]["first_seen"] == first_seen
    assert data2["stats"]["new_this_run"] == 0


def test_failed_source_keeps_old_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(TelegramChannel, "fetch", fake_fetch)
    out = tmp_path / "jobs.json"
    pipeline.run(CONFIG, out, notify=False)

    def boom(self):
        raise RuntimeError("network down")
    monkeypatch.setattr(TelegramChannel, "fetch", boom)
    pipeline.run(CONFIG, out, notify=False)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 1
    assert not any(s["ok"] for s in data["sources"])
    assert all(s["last_ok"] for s in data["sources"])
    assert "network down" in data["sources"][0]["error"]
