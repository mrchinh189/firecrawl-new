"""Per-source parsers that turn a Firecrawl scrape result into price records.

Each parser declares which Firecrawl formats it needs (``FORMATS``) and a
``parse(data, source, today)`` function returning a list of ``PriceRecord``.
Deterministic parsers are preferred (free, no LLM needed); the ``llm_json``
parser is a generic fallback for new sources and requires the Firecrawl
instance to have an LLM configured (OPENAI_API_KEY or OLLAMA_BASE_URL).
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable


class ParseError(ValueError):
    pass


@dataclass
class PriceRecord:
    code: str
    name: str
    price_date: date
    price: float
    unit: str
    url: str
    note: str = ""
    source_id: str = ""


def to_number(text: str) -> float:
    """Parse '1,121.25' / '4554' / '1710.00' into a float."""
    cleaned = text.strip().replace(",", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", cleaned):
        raise ParseError(f"not a number: {text!r}")
    return float(cleaned)


def infer_year(month: int, day: int, today: date) -> date:
    """Dates like '10-03' or '02/10' carry no year: pick the most recent past one."""
    candidate = date(today.year, month, day)
    if candidate > today:
        candidate = date(today.year - 1, month, day)
    return candidate


def markdown_table_rows(markdown: str) -> list[list[str]]:
    rows = []
    for line in markdown.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) or c == "" for c in cells):
            continue
        rows.append(cells)
    return rows


def _record(source: dict, price_date: date, price: float, code: str | None = None,
            name: str | None = None, note: str = "") -> PriceRecord:
    return PriceRecord(
        code=code or source["id"],
        name=name or source["name"],
        price_date=price_date,
        price=price,
        unit=source.get("unit", ""),
        url=source["url"],
        note=note,
        source_id=source["id"],
    )


# --------------------------------------------------------------------------- #
# MPOC – https://www.mpoc.org.my/market-insight/daily-palm-oil-prices/
# Table "CPO Prices": | Pricing Date | Settlement Price RM |  e.g. | 1 Oct 26 | 4554 |
# --------------------------------------------------------------------------- #
def parse_mpoc(data: dict, source: dict, today: date) -> list[PriceRecord]:
    records = []
    for cells in markdown_table_rows(data.get("markdown", "")):
        if len(cells) < 2:
            continue
        try:
            d = datetime.strptime(cells[0], "%d %b %y").date()
            price = to_number(cells[1])
        except ValueError:
            continue
        records.append(_record(source, d, price, note="Settlement price (Bursa Malaysia)"))
    if not records:
        raise ParseError("MPOC: CPO price table not found")
    return records


# --------------------------------------------------------------------------- #
# 100ppi (生意社) – https://m1.100ppi.com/vane/236-硫酸.html
# Table: | 日期 | 价格 | 日涨跌 |  e.g. | 10-03 | 1710.00 | 0.00% |  ('-' = not yet published)
# --------------------------------------------------------------------------- #
def parse_ppi100(data: dict, source: dict, today: date) -> list[PriceRecord]:
    records = []
    for cells in markdown_table_rows(data.get("markdown", "")):
        if len(cells) < 2:
            continue
        m = re.fullmatch(r"(\d{1,2})-(\d{1,2})", cells[0])
        if not m:
            continue
        try:
            price = to_number(cells[1])
        except ParseError:
            continue  # today's price is '-' until ~14:00 China time
        d = infer_year(int(m.group(1)), int(m.group(2)), today)
        note = f"Daily change {cells[2]}" if len(cells) > 2 else ""
        records.append(_record(source, d, price, note=note))
    if not records:
        raise ParseError("100ppi: price table not found")
    return records


# --------------------------------------------------------------------------- #
# Investing.com – commodity pages (e.g. Malaysian Crude Palm Oil Futures CPOc1)
# The page embeds a JSON blob in <meta name="global-translation-variables">
# with LAST_PRICE / PREV_CLOSE. Fallback: the price block in the markdown.
# --------------------------------------------------------------------------- #
_INVESTING_PRICE_MD = re.compile(
    r"^\s*([\d,]+(?:\.\d+)?)\s*\n\s*\n?\s*([+-]?[\d,]+(?:\.\d+)?)\s*\(([+-]?[\d.]+)%\)",
    re.MULTILINE,
)
_INVESTING_DATE_MD = re.compile(r"·\s*(\d{1,2})/(\d{1,2})")


def parse_investing(data: dict, source: dict, today: date) -> list[PriceRecord]:
    markdown = data.get("markdown", "")
    metadata = data.get("metadata") or {}

    price = None
    note = ""
    raw_vars = metadata.get("global-translation-variables")
    if isinstance(raw_vars, list):
        raw_vars = raw_vars[0] if raw_vars else None
    if raw_vars:
        try:
            parsed = json.loads(raw_vars)
            if isinstance(parsed, str):  # value is double-encoded
                parsed = json.loads(parsed)
            price = to_number(parsed["LAST_PRICE"])
            if parsed.get("PREV_CLOSE"):
                note = f"Prev close {parsed['PREV_CLOSE']} {parsed.get('CUR_SYMBOL', '')}".strip()
        except (ValueError, KeyError, TypeError):
            price = None

    if price is None:
        m = _INVESTING_PRICE_MD.search(markdown)
        if not m:
            raise ParseError("Investing: last price not found")
        price = to_number(m.group(1))
        note = f"Change {m.group(2)} ({m.group(3)}%)"

    # "Đóng cửa·02/10" / "Closed·02/10" → dd/mm of the last close
    price_date = today
    m = _INVESTING_DATE_MD.search(markdown)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            price_date = infer_year(month, day, today)
    return [_record(source, price_date, price, note=note)]


# --------------------------------------------------------------------------- #
# LME – official prices JSON API used by the metal pages, e.g.
# https://www.lme.com/api/trading-data/day-delayed?datasourceId=<id>
# Rows: Cash / 3-month with Values [bid, offer]. The official settlement
# price is the Cash offer.
# --------------------------------------------------------------------------- #
def _extract_json(text: str) -> Any:
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ParseError("no JSON object in response")
    return json.loads(text[start : end + 1])


def parse_lme(data: dict, source: dict, today: date) -> list[PriceRecord]:
    payload = _extract_json(data.get("rawHtml") or data.get("markdown") or "")
    wanted = {r.lower() for r in source.get("lme_rows", ["Cash", "3-month"])}
    records = []
    for row in payload.get("Rows", []):
        title = row.get("RowTitle", "")
        if title.lower() not in wanted:
            continue
        values = row.get("Values") or []
        if len(values) < 2:
            continue
        bid, offer = to_number(values[0]), to_number(values[1])
        d = datetime.fromisoformat(row["BusinessDateTime"][:10]).date()
        suffix = re.sub(r"[^A-Z0-9]+", "_", title.upper()).strip("_")
        records.append(
            _record(
                source,
                d,
                offer,
                code=f"{source['id']}_{suffix}",
                name=f"{source['name']} – {title}",
                note=f"Bid {bid:g} / Offer {offer:g}",
            )
        )
    if not records:
        raise ParseError("LME: no Cash/3-month rows in API response")
    return records


# --------------------------------------------------------------------------- #
# Generic LLM extraction (Firecrawl "json" format) for any new source.
# --------------------------------------------------------------------------- #
LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "price": {"type": "number", "description": "Latest price as a plain number"},
        "price_date": {"type": "string", "description": "Date of that price, YYYY-MM-DD"},
        "unit": {"type": "string", "description": "Currency and unit, e.g. USD/tonne"},
    },
    "required": ["price"],
}


def llm_formats(source: dict) -> list[Any]:
    prompt = source.get(
        "llm_prompt",
        f"Extract the latest price of {source['name']} shown on this page.",
    )
    return [{"type": "json", "schema": LLM_SCHEMA, "prompt": prompt}]


def parse_llm_json(data: dict, source: dict, today: date) -> list[PriceRecord]:
    extracted = data.get("json") or {}
    if extracted.get("price") is None:
        raise ParseError("LLM extraction returned no price")
    try:
        price_date = date.fromisoformat(str(extracted.get("price_date"))[:10])
    except ValueError:
        price_date = today
    rec = _record(source, price_date, float(extracted["price"]), note="LLM extracted")
    if not rec.unit and extracted.get("unit"):
        rec.unit = extracted["unit"]
    return [rec]


@dataclass
class Parser:
    formats: Callable[[dict], list[Any]]
    parse: Callable[[dict, dict, date], list[PriceRecord]]
    scrape_options: dict[str, Any] = field(default_factory=dict)


PARSERS: dict[str, Parser] = {
    "mpoc": Parser(lambda s: ["markdown"], parse_mpoc, {"onlyMainContent": True}),
    "ppi100": Parser(lambda s: ["markdown"], parse_ppi100, {"onlyMainContent": True}),
    "investing": Parser(lambda s: ["markdown"], parse_investing, {"onlyMainContent": True}),
    "lme": Parser(lambda s: ["rawHtml"], parse_lme),
    "llm_json": Parser(llm_formats, parse_llm_json, {"onlyMainContent": True}),
}
