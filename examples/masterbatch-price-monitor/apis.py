"""Nạp giá từ các API trực tiếp (không qua Firecrawl): FRED, EIA, Sina, Comtrade.

Mọi hàm trả về danh sách dict chuẩn hóa giống dữ liệu cào web:
    {ten_vat_lieu, nhom, gia, don_vi, nha_cung_cap, ngay_bao_gia, _nguon_url}
Mỗi nguồn bọc try/except để một nguồn lỗi không làm hỏng cả lần chạy.
"""

import os
import requests

from config import (
    FRED_SERIES,
    EIA_REQUESTS, EIA_BASE,
    SINA_SYMBOLS, SINA_URL, SINA_REFERER,
    COMTRADE_REQUESTS,
)

TIMEOUT = 30


def _row(ten, nhom, gia, don_vi, nguon, ngay=None, url=""):
    return {
        "ten_vat_lieu": ten,
        "nhom": nhom,
        "gia": gia,
        "don_vi": don_vi,
        "nha_cung_cap": nguon,
        "ngay_bao_gia": ngay,
        "_nguon_url": url,
    }


# --------------------------------------------------------------------------
# FRED — https://api.stlouisfed.org/fred/series/observations
# --------------------------------------------------------------------------
def fetch_fred() -> list[dict]:
    key = os.getenv("FRED_API_KEY")
    if not key or not FRED_SERIES:
        return []
    rows: list[dict] = []
    for series_id, ten, don_vi, nhom in FRED_SERIES:
        try:
            r = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series_id,
                    "api_key": key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 1,
                },
                timeout=TIMEOUT,
            )
            r.raise_for_status()
            obs = r.json().get("observations", [])
            if not obs:
                continue
            val = obs[0].get("value")
            if val in (None, "", "."):
                continue
            rows.append(_row(
                ten, nhom, float(val), don_vi, "FRED",
                ngay=obs[0].get("date"),
                url=f"https://fred.stlouisfed.org/series/{series_id}",
            ))
            print(f"[FRED] {series_id} = {val} ({obs[0].get('date')})")
        except Exception as e:  # noqa: BLE001
            print(f"[FRED][LỖI] {series_id}: {e}")
    return rows


# --------------------------------------------------------------------------
# EIA v2 — https://api.eia.gov/v2/petroleum/pri/spt/data/
# --------------------------------------------------------------------------
def fetch_eia() -> list[dict]:
    key = os.getenv("EIA_API_KEY")
    if not key or not EIA_REQUESTS:
        return []
    rows: list[dict] = []
    for ten, don_vi, nhom, extra in EIA_REQUESTS:
        try:
            params = {
                "api_key": key,
                "frequency": "daily",
                "data[0]": "value",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": "1",
            }
            params.update(extra)
            r = requests.get(EIA_BASE, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json().get("response", {}).get("data", [])
            if not data:
                continue
            rec = data[0]
            val = rec.get("value")
            if val is None:
                continue
            rows.append(_row(
                ten, nhom, float(val), don_vi, "EIA",
                ngay=rec.get("period"), url=EIA_BASE,
            ))
            print(f"[EIA] {ten} = {val} ({rec.get('period')})")
        except Exception as e:  # noqa: BLE001
            print(f"[EIA][LỖI] {ten}: {e}")
    return rows


# --------------------------------------------------------------------------
# Sina — https://hq.sinajs.cn/list=nf_PP0,nf_L0  (cần Referer)
# Trả về dạng: var hq_str_nf_PP0="名称,...,giá,...";
# --------------------------------------------------------------------------
def fetch_sina() -> list[dict]:
    if not SINA_SYMBOLS:
        return []
    try:
        r = requests.get(
            SINA_URL + ",".join(SINA_SYMBOLS.keys()),
            headers={"Referer": SINA_REFERER, "User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT,
        )
        r.encoding = "gbk"  # Sina trả về GBK
        r.raise_for_status()
    except Exception as e:  # noqa: BLE001
        print(f"[Sina][LỖI] {e}")
        return []

    rows: list[dict] = []
    for line in r.text.splitlines():
        if "=" not in line or '"' not in line:
            continue
        try:
            sym = line.split("hq_str_")[1].split("=")[0].strip()
            payload = line.split('"')[1]
            fields = payload.split(",")
            if sym not in SINA_SYMBOLS or len(fields) < 2:
                continue
            ten, nhom, don_vi, idx = SINA_SYMBOLS[sym]
            if idx >= len(fields):
                continue
            gia = float(fields[idx])
            rows.append(_row(
                ten, nhom, gia, don_vi, "Sina/DCE",
                url=f"https://finance.sina.com.cn/futures/quotes/{sym.split('_')[1]}.shtml",
            ))
            print(f"[Sina] {sym} = {gia}")
        except Exception as e:  # noqa: BLE001
            print(f"[Sina][LỖI] dòng '{line[:40]}...': {e}")
    return rows


# --------------------------------------------------------------------------
# UN Comtrade — tùy chọn (dữ liệu thương mại theo tháng). Mặc định TẮT.
# --------------------------------------------------------------------------
def fetch_comtrade() -> list[dict]:
    key = os.getenv("COMTRADE_PRIMARY_KEY")
    if not key or not COMTRADE_REQUESTS:
        return []
    rows: list[dict] = []
    for req in COMTRADE_REQUESTS:
        try:
            url = req["url"]
            params = dict(req.get("params", {}))
            params["subscription-key"] = key
            r = requests.get(url, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            for rec in r.json().get("data", []):
                # unit value = trade value / quantity (xấp xỉ giá xuất/nhập)
                val = rec.get("primaryValue")
                qty = rec.get("qty") or rec.get("netWgt")
                if not val or not qty:
                    continue
                rows.append(_row(
                    req.get("ten", rec.get("cmdDesc", "Comtrade")),
                    "thuong_mai", float(val) / float(qty),
                    req.get("don_vi", "USD/đơn vị"), "UN Comtrade",
                    ngay=str(rec.get("period")), url=url,
                ))
        except Exception as e:  # noqa: BLE001
            print(f"[Comtrade][LỖI] {e}")
    return rows


def fetch_all_apis() -> list[dict]:
    rows: list[dict] = []
    rows += fetch_fred()
    rows += fetch_eia()
    rows += fetch_sina()
    rows += fetch_comtrade()
    return rows
