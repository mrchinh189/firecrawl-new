"""Local CSV storage with the same interface as SheetStore.

Used when GOOGLE_SHEET_ID is not set: handy for testing the pipeline before
wiring up Google Sheets, or as a local backup.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from .parsers import PriceRecord
from .sheets import HISTORY_HEADER, LATEST_HEADER


class CsvStore:
    def __init__(self, directory: str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.history_path = self.dir / "lich_su_gia.csv"
        self.latest_path = self.dir / "gia_moi_nhat.csv"

    def load_history(self) -> dict[str, dict[date, float]]:
        history: dict[str, dict[date, float]] = {}
        if not self.history_path.exists():
            return history
        with self.history_path.open(encoding="utf-8-sig", newline="") as f:
            for row in list(csv.reader(f))[1:]:
                try:
                    history.setdefault(row[1], {})[date.fromisoformat(row[3])] = float(row[4])
                except (ValueError, IndexError):
                    continue
        return history

    def load_latest(self) -> list[list[str]]:
        if not self.latest_path.exists():
            return []
        with self.latest_path.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))[1:]

    def append_history(self, rows: Iterable[tuple[PriceRecord, float | None]], scraped_at: datetime):
        new_file = not self.history_path.exists()
        with self.history_path.open("a", encoding="utf-8-sig" if new_file else "utf-8", newline="") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow(HISTORY_HEADER)
            for r, pct in rows:
                w.writerow([
                    scraped_at.strftime("%Y-%m-%d %H:%M"), r.code, r.name, r.price_date.isoformat(),
                    r.price, r.unit, "" if pct is None else round(pct, 2), r.note, r.url,
                ])

    def write_latest(self, rows: list[list]):
        with self.latest_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(LATEST_HEADER)
            w.writerows(rows)
