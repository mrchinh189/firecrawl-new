"""Test logic tính giá thành (khớp/loại trừ/chọn rẻ nhất). Không cần DB.
Chạy: python -m pytest test_costing.py  hoặc  python test_costing.py"""

from costing import cost_from_normalized, _match, _recipe_row


def _row(ten, gia, ncc="X"):
    return {"ten_vat_lieu": ten, "nha_cung_cap": ncc, "vnd_per_kg": gia}


RECIPE = [
    ("PE nền", ["lldpe", "ldpe", "hdpe", "polyethylene"], 0.8, 30000.0, ["wax"]),
    ("Phụ gia", ["stearic", "pe wax", "polyethylene wax"], 0.2, 40000.0, []),
]


def test_exclude_chan_wax_khoi_pe_nen():
    # "Polyethylene wax" rẻ hơn nhưng phải bị loại khỏi PE nền nhờ exclude=["wax"]
    norm = [_row("LLDPE Film", 32000), _row("Polyethylene wax", 28000)]
    tong, bd = cost_from_normalized(norm, RECIPE)
    assert bd[0]["don_gia_vnd_kg"] == 32000          # chọn LLDPE, không phải wax
    assert "Polyethylene wax" in bd[1]["nguon"]      # wax về đúng nhóm phụ gia


def test_chon_nguon_re_nhat():
    norm = [_row("LLDPE A", 33000, "NCC1"), _row("LLDPE B", 31000, "NCC2")]
    _, bd = cost_from_normalized(norm, RECIPE)
    assert bd[0]["don_gia_vnd_kg"] == 31000 and "NCC2" in bd[0]["nguon"]


def test_fallback_khi_khong_co_du_lieu():
    tong, bd = cost_from_normalized([], RECIPE)
    assert bd[0]["nguon"] == "giá dự phòng"
    assert abs(tong - (30000 * 0.8 + 40000 * 0.2)) < 1e-6


def test_tong_co_trong_so():
    norm = [_row("HDPE", 30000), _row("Stearic acid", 40000)]
    tong, _ = cost_from_normalized(norm, RECIPE)
    assert abs(tong - (30000 * 0.8 + 40000 * 0.2)) < 1e-6


def test_stearic_khong_lan_stearate():
    # "stearic" KHÔNG phải substring của "stearate" -> zinc stearate không bị bắt
    assert _match("Zinc stearate", ["stearic"], []) is False
    assert _match("Stearic acid", ["stearic"], []) is True


def test_recipe_row_tuong_thich_4_va_5_phan_tu():
    assert _recipe_row(("A", ["a"], 0.5, 100.0))[4] == []        # tuple 4 -> exclude rỗng
    assert _recipe_row(("A", ["a"], 0.5, 100.0, ["x"]))[4] == ["x"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} test OK")
