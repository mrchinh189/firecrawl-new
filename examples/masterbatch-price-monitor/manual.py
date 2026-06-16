"""Nạp báo giá NCC nhập tay từ CSV cho các mã không có nguồn web tự động.

CSV cột: code,gia,don_vi,nha_cung_cap,ngay
Mã (code) phải khớp với CATALOG trong config.MATERIALS để lấy tên/nhóm.
"""

import csv
import os

from config import MATERIALS

_BY_CODE = {m["code"]: m for m in MATERIALS}


def manual_only_codes() -> list[str]:
    """Mã chỉ có nguồn 'NCC báo giá' (không businessanalytiq, không Sina)."""
    return [m["code"] for m in MATERIALS if not m.get("ba") and not m.get("sina")]


def load_manual_prices(path: str) -> list[dict]:
    if not path or not os.path.exists(path):
        return []
    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for rec in csv.DictReader(f):
            code = (rec.get("code") or "").strip()
            gia = (rec.get("gia") or "").strip()
            if not code or not gia:
                continue
            try:
                gia_f = float(gia.replace(",", ""))
            except ValueError:
                continue
            mat = _BY_CODE.get(code)
            ten = mat["ten"] if mat else code
            nhom = mat["nhom"] if mat else "khac"
            rows.append({
                "ten_vat_lieu": ten,
                "nhom": nhom,
                "gia": gia_f,
                "don_vi": (rec.get("don_vi") or "VND/kg").strip(),
                "nha_cung_cap": (rec.get("nha_cung_cap") or "NCC").strip(),
                "ngay_bao_gia": (rec.get("ngay") or "").strip() or None,
                "_nguon_url": "(báo giá NCC)",
            })
    print(f"[manual] nạp {len(rows)} báo giá NCC từ {path}")
    return rows
