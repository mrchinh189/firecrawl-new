"""Price history storage in Google Sheets (via a service account)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from .parsers import PriceRecord

HISTORY_HEADER = [
    "Thời điểm cào",
    "Mã",
    "Tên NVL",
    "Ngày giá",
    "Giá",
    "Đơn vị",
    "% thay đổi",
    "Ghi chú",
    "Nguồn",
]
LATEST_HEADER = [
    "Mã",
    "Tên NVL",
    "Ngày giá",
    "Giá",
    "Đơn vị",
    "Giá trước",
    "% thay đổi",
    "Cập nhật lúc",
    "Nguồn",
]


def _ensure_worksheet(spreadsheet, title: str, header: list[str]):
    import gspread

    try:
        ws = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(header))
    if ws.row_values(1) != header:
        ws.update(range_name="A1", values=[header])
        ws.freeze(rows=1)
    return ws


class SheetStore:
    def __init__(self, service_account_file: str, sheet_id: str,
                 history_tab: str = "LichSuGia", latest_tab: str = "GiaMoiNhat"):
        import gspread

        client = gspread.service_account(filename=service_account_file)
        self.spreadsheet = client.open_by_key(sheet_id)
        self.history = _ensure_worksheet(self.spreadsheet, history_tab, HISTORY_HEADER)
        self.latest = _ensure_worksheet(self.spreadsheet, latest_tab, LATEST_HEADER)

    def load_history(self) -> dict[str, dict[date, float]]:
        """Return {code: {price_date: price}} from the history tab."""
        history: dict[str, dict[date, float]] = {}
        for row in self.history.get_all_values()[1:]:
            if len(row) < 5 or not row[1]:
                continue
            try:
                d = date.fromisoformat(row[3])
                price = float(str(row[4]).replace(",", ""))
            except ValueError:
                continue
            history.setdefault(row[1], {})[d] = price
        return history

    def load_latest(self) -> list[list[str]]:
        return [r for r in self.latest.get_all_values()[1:] if r and r[0]]

    def append_history(self, rows: Iterable[tuple[PriceRecord, float | None]], scraped_at: datetime):
        values = [
            [
                scraped_at.strftime("%Y-%m-%d %H:%M"),
                r.code,
                r.name,
                r.price_date.isoformat(),
                r.price,
                r.unit,
                "" if pct is None else round(pct, 2),
                r.note,
                r.url,
            ]
            for r, pct in rows
        ]
        if values:
            self.history.append_rows(values, value_input_option="USER_ENTERED")

    def write_latest(self, rows: list[list]):
        self.latest.batch_clear(["A2:Z1000"])
        if rows:
            self.latest.update(range_name="A2", values=rows, value_input_option="USER_ENTERED")
