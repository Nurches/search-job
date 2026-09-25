"""CLI агрегатора.

  python -m aggregator run            собрать заказы в site/data/jobs.json
  python -m aggregator run --only tg  только источники, чей id совпадает с regex
  python -m aggregator check          проверить все источники (без сохранения)
  python -m aggregator demo           демо-данные, чтобы посмотреть сайт без сети
  python -m aggregator serve          открыть сайт на http://localhost:8000
"""
from __future__ import annotations

import argparse
import functools
import http.server
import logging
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.yaml"
DEFAULT_OUT = ROOT / "site" / "data" / "jobs.json"


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aggregator")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="собрать заказы")
    p_run.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p_run.add_argument("--only", help="regex по id источника")
    p_run.add_argument("--no-notify", action="store_true")

    p_check = sub.add_parser("check", help="проверить источники")
    p_check.add_argument("--only", help="regex по id источника")

    p_demo = sub.add_parser("demo", help="демо-данные")
    p_demo.add_argument("--out", type=Path, default=DEFAULT_OUT)

    p_serve = sub.add_parser("serve", help="локальный сервер")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    config = load_config(args.config)

    if args.cmd == "run":
        from .pipeline import run
        run(config, args.out, notify=not args.no_notify, only=args.only)
        return 0

    if args.cmd == "check":
        from .classify import rejection_reason
        from .pipeline import fetch_all
        from .sources import build_sources
        sources = build_sources(config)
        if args.only:
            sources = [s for s in sources if re.search(args.only, s.id)]
        results, health = fetch_all(sources)
        accepted: dict[str, int] = {}
        for src, job in results:
            if not rejection_reason(job, src.cfg):
                accepted[src.id] = accepted.get(src.id, 0) + 1
        print(f"\n{'источник':30} {'статус':8} {'всего':>6} {'IT':>5}")
        for h in health:
            status = "OK" if h["ok"] else "ОШИБКА"
            print(f"{h['id'][:30]:30} {status:8} {h['fetched']:6} {accepted.get(h['id'], 0):5}"
                  + (f"   {h['error']}" if h["error"] else ""))
        return 0 if any(h["ok"] for h in health) else 1

    if args.cmd == "demo":
        from .demo import write_demo
        write_demo(config, args.out)
        print(f"демо-данные записаны в {args.out}")
        return 0

    if args.cmd == "serve":
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "site"))
        print(f"http://localhost:{args.port}")
        http.server.ThreadingHTTPServer(("", args.port), handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
