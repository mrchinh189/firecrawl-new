"""Pure logic: merge new records into history, compute % change and alerts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .parsers import PriceRecord


@dataclass
class Alert:
    record: PriceRecord
    prev_date: date
    prev_price: float
    pct: float
    threshold: float


@dataclass
class MergeResult:
    new_rows: list[tuple[PriceRecord, float | None]]
    alerts: list[Alert]
    latest: dict[str, tuple[PriceRecord, float | None, float | None]]  # code -> (rec, prev, pct)


def pct_change(prev: float, cur: float) -> float | None:
    if not prev:
        return None
    return (cur - prev) / prev * 100


def merge(
    records: list[PriceRecord],
    history: dict[str, dict[date, float]],
    thresholds: dict[str, float],
    default_threshold: float,
) -> MergeResult:
    """Merge scraped records into ``history`` (mutated in place).

    - A (code, price_date) pair already in history is not stored again, so
      re-running the job the same day, or re-reading a table that still lists
      older days, never creates duplicates.
    - Older rows a page shows (e.g. MPOC's last 10 days) backfill history on
      the first run.
    - Only the newest *new* price per code can raise an alert.
    """
    by_code: dict[str, list[PriceRecord]] = {}
    for r in records:
        by_code.setdefault(r.code, []).append(r)

    new_rows: list[tuple[PriceRecord, float | None]] = []
    alerts: list[Alert] = []
    latest: dict[str, tuple[PriceRecord, float | None, float | None]] = {}

    for code, recs in by_code.items():
        series = history.setdefault(code, {})
        newest_new: tuple[PriceRecord, date, float, float] | None = None
        for rec in sorted(recs, key=lambda r: r.price_date):
            if rec.price_date in series:
                continue
            earlier = [d for d in series if d < rec.price_date]
            pct = None
            if earlier:
                prev_d = max(earlier)
                pct = pct_change(series[prev_d], rec.price)
                if pct is not None:
                    newest_new = (rec, prev_d, series[prev_d], pct)
            series[rec.price_date] = rec.price
            new_rows.append((rec, pct))

        if newest_new and newest_new[0].price_date == max(series):
            rec, prev_d, prev_p, pct = newest_new
            threshold = thresholds.get(rec.source_id, default_threshold)
            if abs(pct) >= threshold:
                alerts.append(Alert(rec, prev_d, prev_p, pct, threshold))

        newest_rec = max(recs, key=lambda r: r.price_date)
        if newest_rec.price_date == max(series):
            dates = sorted(series)
            prev = series[dates[-2]] if len(dates) > 1 else None
            latest[code] = (newest_rec, prev, pct_change(prev, newest_rec.price) if prev else None)

    return MergeResult(new_rows, alerts, latest)


def format_alerts(alerts: list[Alert], failures: list[str]) -> str:
    lines = []
    for a in alerts:
        arrow = "▲" if a.pct > 0 else "▼"
        r = a.record
        lines.append(
            f"{arrow} {r.name}: {r.price:,.2f} {r.unit} ({a.pct:+.2f}%)\n"
            f"   {a.prev_date:%d/%m} {a.prev_price:,.2f} → {r.price_date:%d/%m} {r.price:,.2f}"
            f" (ngưỡng {a.threshold:g}%)\n   {r.url}"
        )
    if failures:
        lines.append("⚠️ Nguồn lỗi:\n" + "\n".join(f"   - {f}" for f in failures))
    return "\n\n".join(lines)
