"""Entry point: scrape every configured source, store prices, send alerts.

    python -m nvl_tracker.tracker                 # run once (cron daily)
    python -m nvl_tracker.tracker --dry-run       # print only, store nothing, no alerts
    python -m nvl_tracker.tracker --only ZINC_LME # run a single source
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .alerts import notify
from .core import format_alerts, merge
from .firecrawl_client import FirecrawlClient, ScrapeError
from .parsers import PARSERS, ParseError, PriceRecord

log = logging.getLogger("nvl_tracker")
ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Tiny .env loader (KEY=VALUE lines) so python-dotenv is not required."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def scrape_source(client: FirecrawlClient, source: dict, today: date) -> list[PriceRecord]:
    parser = PARSERS.get(source["parser"])
    if parser is None:
        raise ParseError(f"unknown parser {source['parser']!r} (available: {', '.join(PARSERS)})")
    options = {**parser.scrape_options, **source.get("scrape_options", {})}
    data = client.scrape(source["url"], parser.formats(source), **options)
    return parser.parse(data, source, today)


def build_store(dry_run: bool):
    if dry_run:
        return None
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if sheet_id:
        from .sheets import SheetStore

        return SheetStore(
            os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", str(ROOT / "service_account.json")),
            sheet_id,
        )
    from .csv_store import CsvStore

    directory = os.getenv("CSV_OUTPUT_DIR", str(ROOT / "data"))
    log.info("GOOGLE_SHEET_ID not set – writing CSV files to %s", directory)
    return CsvStore(directory)


def latest_rows(existing: list[list[str]], latest: dict, updated_at: datetime) -> list[list]:
    """Upsert into the 'latest' tab so a source that failed today keeps its last value."""
    rows = {r[0]: r for r in existing if r}
    for code, (rec, prev, pct) in latest.items():
        rows[code] = [
            rec.code, rec.name, rec.price_date.isoformat(), rec.price, rec.unit,
            "" if prev is None else prev, "" if pct is None else round(pct, 2),
            updated_at.strftime("%Y-%m-%d %H:%M"), rec.url,
        ]
    return [rows[k] for k in sorted(rows)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Theo dõi giá nguyên vật liệu bằng Firecrawl")
    ap.add_argument("--config", default=str(ROOT / "sources.yaml"))
    ap.add_argument("--dry-run", action="store_true", help="chỉ in kết quả, không lưu, không cảnh báo")
    ap.add_argument("--no-alert", action="store_true", help="lưu dữ liệu nhưng không gửi cảnh báo")
    ap.add_argument("--only", nargs="*", help="chỉ chạy các source id này")
    args = ap.parse_args(argv)

    load_env_file(ROOT / ".env")
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    tz = ZoneInfo(config.get("timezone", "Asia/Ho_Chi_Minh"))
    now = datetime.now(tz)
    today = now.date()

    client = FirecrawlClient(
        api_url=os.getenv("FIRECRAWL_API_URL", "http://localhost:3002"),
        api_key=os.getenv("FIRECRAWL_API_KEY", ""),
        fallback_api_key=os.getenv("FIRECRAWL_FALLBACK_API_KEY", ""),
        timeout_ms=int(config.get("scrape_timeout_ms", 60000)),
    )

    sources = [s for s in config["sources"] if s.get("enabled", True)]
    if args.only:
        sources = [s for s in sources if s["id"] in args.only]

    records: list[PriceRecord] = []
    failures: list[str] = []
    for source in sources:
        try:
            got = scrape_source(client, source, today)
            newest = max(got, key=lambda r: r.price_date)
            log.info("%-16s %d record(s), newest %s = %s %s", source["id"], len(got),
                     newest.price_date, newest.price, newest.unit)
            records.extend(got)
        except (ScrapeError, ParseError, ValueError) as exc:
            log.error("%s failed: %s", source["id"], exc)
            failures.append(f"{source['id']} ({source['url']}): {exc}")

    store = build_store(args.dry_run)
    history = store.load_history() if store else {}
    thresholds = {s["id"]: float(s["alert_threshold_pct"]) for s in sources if "alert_threshold_pct" in s}
    result = merge(records, history, thresholds, float(config.get("alert_threshold_pct", 2.0)))

    for rec, pct in result.new_rows:
        pct_s = "" if pct is None else f"{pct:+.2f}%"
        print(f"{rec.code:22} {rec.price_date}  {rec.price:>12,.2f} {rec.unit:10} {pct_s:>8}  {rec.note}")

    if store:
        store.append_history(result.new_rows, now)
        store.write_latest(latest_rows(store.load_latest(), result.latest, now))
        log.info("Stored %d new row(s)", len(result.new_rows))

    if result.alerts or failures:
        body = format_alerts(result.alerts, failures)
        subject = f"[Giá NVL] {len(result.alerts)} biến động" + (f", {len(failures)} nguồn lỗi" if failures else "")
        if args.dry_run or args.no_alert:
            print(f"\n--- {subject} (không gửi) ---\n{body}")
        else:
            notify(subject, body)

    # Non-zero exit only when every source failed, so cron/monitoring notices.
    return 1 if sources and len(failures) == len(sources) else 0


if __name__ == "__main__":
    sys.exit(main())
