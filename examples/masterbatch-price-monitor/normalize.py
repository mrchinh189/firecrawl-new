"""Quy đổi mọi mức giá về cùng một đơn vị: VND/kg.

Nguồn dữ liệu dùng nhiều đơn vị (USD/MT, cents/lb, RM/tonne, CNY/tấn, VND/kg...).
Module này phân tích chuỗi đơn vị và quy đổi dùng tỷ giá thu thập được.
"""

from config import FX_FALLBACK

# kg cho 1 đơn vị khối lượng
_WEIGHT_TO_KG = {
    "kg": 1.0, "kgs": 1.0, "kilogram": 1.0,
    "mt": 1000.0, "tonne": 1000.0, "tonnes": 1000.0, "ton": 1000.0,
    "tons": 1000.0, "tấn": 1000.0, "tan": 1000.0, "t": 1000.0,
    "lb": 0.45359237, "lbs": 0.45359237, "pound": 0.45359237, "pounds": 0.45359237,
    "g": 0.001, "gram": 0.001,
}

# hệ số tiền tệ về "đơn vị gốc" (cents -> 0.01 USD)
_CENTS = {"cents", "cent", "¢", "us-cents", "uscents"}


def _split_unit(don_vi: str):
    """'USD/MT' -> ('usd', 'mt'); 'cents/lb' -> ('cents','lb'); 'CNY/tấn' -> ('cny','tấn')."""
    s = (don_vi or "").lower().strip().replace("per", "/").replace(" ", "")
    s = s.replace("vnđ", "vnd").replace("đồng", "vnd").replace("rmb", "cny").replace("yuan", "cny")
    s = s.replace("rm", "myr").replace("ringgit", "myr").replace("us$", "usd").replace("$", "usd")
    if "/" not in s:
        return None, None
    cur, _, wt = s.partition("/")
    return cur, wt


def to_vnd_per_kg(gia: float, don_vi: str, fx: dict) -> tuple:
    """Trả về (gia_vnd_per_kg, True) nếu quy đổi được, ngược lại (None, False)."""
    if gia is None:
        return None, False
    cur, wt = _split_unit(don_vi)
    if not cur or not wt:
        return None, False

    # tiền tệ -> VND cho 1 đơn vị tiền
    money_mult = 1.0
    code = cur
    if cur in _CENTS:
        money_mult = 0.01
        code = "usd"
    code = code.upper()

    if code == "VND":
        vnd_per_unit_currency = 1.0
    else:
        rate = fx.get(code) or FX_FALLBACK.get(code)
        if not rate:
            return None, False
        vnd_per_unit_currency = float(rate)

    # khối lượng
    kg = None
    for token, factor in _WEIGHT_TO_KG.items():
        if wt == token:
            kg = factor
            break
    if kg is None:
        return None, False

    gia_vnd_per_kg = gia * money_mult * vnd_per_unit_currency / kg
    return gia_vnd_per_kg, True
