"""Test quy đổi đơn vị về VND/kg. Chạy: python -m pytest test_normalize.py
(hoặc: python test_normalize.py để chạy nhanh không cần pytest)."""

from normalize import to_vnd_per_kg

FX = {"USD": 25400.0, "CNY": 3500.0, "MYR": 5400.0, "EUR": 27500.0}


def test_usd_per_mt():
    v, ok = to_vnd_per_kg(1200, "USD/MT", FX)
    assert ok and abs(v - 1200 * 25400 / 1000) < 1e-6


def test_cents_per_lb():
    v, ok = to_vnd_per_kg(50, "cents/lb", FX)
    assert ok and abs(v - 50 * 0.01 * 25400 / 0.45359237) < 1e-3


def test_cny_per_tan():
    v, ok = to_vnd_per_kg(7000, "CNY/tấn", FX)
    assert ok and abs(v - 7000 * 3500 / 1000) < 1e-6


def test_rm_per_tonne():
    v, ok = to_vnd_per_kg(4000, "RM/tonne", FX)
    assert ok and abs(v - 4000 * 5400 / 1000) < 1e-6


def test_vnd_passthrough():
    v, ok = to_vnd_per_kg(2500, "VND/kg", FX)
    assert ok and abs(v - 2500) < 1e-9


def test_barrel_not_weight():
    # Dầu thô USD/barrel KHÔNG phải đơn vị khối lượng -> không quy đổi
    _, ok = to_vnd_per_kg(95, "USD/barrel", FX)
    assert ok is False


def test_missing_fx():
    # Thiếu tỷ giá JPY -> không quy đổi được
    _, ok = to_vnd_per_kg(100, "JPY/kg", FX)
    assert ok is False


def test_none_price():
    _, ok = to_vnd_per_kg(None, "USD/MT", FX)
    assert ok is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} test OK")
