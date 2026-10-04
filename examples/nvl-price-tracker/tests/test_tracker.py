import json
from datetime import date
from pathlib import Path

import pytest

from nvl_tracker.core import merge
from nvl_tracker.csv_store import CsvStore
from nvl_tracker.parsers import (
    ParseError,
    parse_investing,
    parse_lme,
    parse_mpoc,
    parse_ppi100,
)
from nvl_tracker.tracker import latest_rows

FIX = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 4)


def src(id_, unit="X", **kw):
    return {"id": id_, "name": id_, "url": f"https://example.com/{id_}", "unit": unit, **kw}


def test_mpoc_reads_cpo_table_only():
    recs = parse_mpoc({"markdown": (FIX / "mpoc.md").read_text()}, src("CPO_MPOC"), TODAY)
    assert len(recs) == 10  # the monthly US$ table is ignored
    newest = max(recs, key=lambda r: r.price_date)
    assert (newest.price_date, newest.price) == (date(2026, 10, 1), 4554)


def test_ppi100_skips_unpublished_today_and_infers_year():
    recs = parse_ppi100({"markdown": (FIX / "ppi100.md").read_text()}, src("H2SO4"), TODAY)
    assert len(recs) == 7
    assert max(r.price_date for r in recs) == date(2026, 10, 3)
    assert {r.price for r in recs if r.price_date == date(2026, 9, 23)} == {1737.5}


def test_ppi100_year_rollover():
    md = "| 日期 | 价格 | 日涨跌 |\n| 12-31 | 100.00 | 0.00% |\n| 01-02 | 101.00 | 1.00% |"
    recs = parse_ppi100({"markdown": md}, src("X"), date(2027, 1, 3))
    assert {r.price_date for r in recs} == {date(2026, 12, 31), date(2027, 1, 2)}


def test_investing_from_metadata():
    data = {
        "markdown": (FIX / "investing.md").read_text(),
        "metadata": json.loads((FIX / "investing_metadata.json").read_text()),
    }
    [rec] = parse_investing(data, src("CPO_INV"), TODAY)
    assert rec.price == 1121.25
    assert rec.price_date == date(2026, 10, 2)
    assert "1,191.00" in rec.note


def test_investing_markdown_fallback():
    [rec] = parse_investing({"markdown": (FIX / "investing.md").read_text()}, src("CPO_INV"), TODAY)
    assert rec.price == 1121.25
    assert "-0.47" in rec.note


def test_lme_json_plain_and_wrapped_in_html():
    raw = (FIX / "lme.json").read_text()
    for body in (raw, f"<html><body><pre>{raw}</pre></body></html>"):
        recs = parse_lme({"rawHtml": body}, src("ZINC_LME", lme_rows=["Cash", "3-month"]), TODAY)
        by_code = {r.code: r for r in recs}
        assert set(by_code) == {"ZINC_LME_CASH", "ZINC_LME_3_MONTH"}
        assert by_code["ZINC_LME_CASH"].price == 3798.0  # offer = official price
        assert by_code["ZINC_LME_CASH"].source_id == "ZINC_LME"
        assert by_code["ZINC_LME_CASH"].price_date == date(2026, 10, 2)


@pytest.mark.parametrize(
    "parser,data",
    [
        (parse_mpoc, {"markdown": "Access denied"}),
        (parse_ppi100, {"markdown": "<captcha>"}),
        (parse_investing, {"markdown": "Just a moment...", "metadata": {}}),
        (parse_lme, {"rawHtml": "<html>blocked</html>"}),
    ],
)
def test_parsers_fail_loudly_on_blocked_pages(parser, data):
    with pytest.raises(ParseError):
        parser(data, src("X"), TODAY)


def test_merge_backfills_dedups_and_alerts(tmp_path):
    source = src("CPO_MPOC", unit="RM/tấn")
    recs = parse_mpoc({"markdown": (FIX / "mpoc.md").read_text()}, source, TODAY)
    store = CsvStore(str(tmp_path))

    # First run: whole table is backfilled; 4610 -> 4554 is -1.21%, below a 3% threshold.
    res = merge(recs, store.load_history(), {"CPO_MPOC": 3.0}, 2.0)
    assert len(res.new_rows) == 10
    assert res.alerts == []
    store.append_history(res.new_rows, __import__("datetime").datetime(2026, 10, 4, 8, 0))

    # Second run with the same page: nothing new.
    res = merge(recs, store.load_history(), {"CPO_MPOC": 3.0}, 2.0)
    assert res.new_rows == [] and res.alerts == []

    # Next day the price jumps 5% -> one new row and one alert.
    jump = recs[-1].__class__(**{**recs[-1].__dict__, "price_date": date(2026, 10, 2), "price": 4781.7})
    res = merge(recs + [jump], store.load_history(), {"CPO_MPOC": 3.0}, 2.0)
    assert [r.price_date for r, _ in res.new_rows] == [date(2026, 10, 2)]
    [alert] = res.alerts
    assert alert.prev_price == 4554 and round(alert.pct, 1) == 5.0
    rec, prev, pct = res.latest["CPO_MPOC"]
    assert rec.price == 4781.7 and prev == 4554


def test_latest_rows_keeps_sources_that_failed_today():
    existing = [["ZINC_LME_CASH", "Kẽm", "2026-10-01", "3700", "USD/tấn", "", "", "", ""]]
    recs = parse_ppi100({"markdown": (FIX / "ppi100.md").read_text()}, src("H2SO4"), TODAY)
    res = merge(recs, {}, {}, 2.0)
    rows = latest_rows(existing, res.latest, __import__("datetime").datetime(2026, 10, 4))
    assert [r[0] for r in rows] == ["H2SO4", "ZINC_LME_CASH"]
