"""Tính giá thành filler masterbatch theo công thức phối trộn.

Quy đổi mọi giá NVL về VND/kg, khớp với từng thành phần công thức (chọn nguồn
rẻ nhất), rồi tính giá thành theo tỷ lệ. Kết quả được lưu lại như một "mặt hàng"
(nhom='gia_thanh') nên tự động lên biểu đồ xu hướng.

Lưu ý: mỗi lần chạy tính giá thành từ GIÁ MỚI NHẤT và lưu 1 điểm. Biểu đồ xu
hướng dựng tích lũy từ lúc bắt đầu chạy trở đi — không hồi tố giá thành quá khứ.
"""

from normalize import to_vnd_per_kg
from config import RECIPE, COST_LABEL

# Các nhóm không phải NVL mua -> không đưa vào tính giá thành.
_EXCLUDE_GROUPS = {"ty_gia", "gia_thanh", "chi_so_vimo"}


def _match(name: str, keywords: list[str], exclude: list[str]) -> bool:
    n = (name or "").lower()
    if any(x in n for x in exclude):
        return False
    return any(k in n for k in keywords)


def _recipe_row(entry):
    """Hỗ trợ cả tuple 4 phần tử (cũ) lẫn 5 phần tử (có exclude)."""
    nhan, keywords, ty_le, fallback = entry[0], entry[1], entry[2], entry[3]
    exclude = entry[4] if len(entry) > 4 else []
    return nhan, keywords, ty_le, fallback, exclude


def cost_from_normalized(normalized: list, recipe: list) -> tuple:
    """Logic thuần (không DB): từ danh sách giá đã quy đổi VND/kg + công thức,
    trả về (tong, breakdown). Tách riêng để test dễ dàng."""
    breakdown = []
    tong = 0.0
    for entry in recipe:
        nhan, keywords, ty_le, fallback, exclude = _recipe_row(entry)
        matches = [r for r in normalized if _match(r["ten_vat_lieu"], keywords, exclude)]
        if matches:
            best = min(matches, key=lambda r: r["vnd_per_kg"])
            don_gia = best["vnd_per_kg"]
            nguon = f"{best['nha_cung_cap']} ({best['ten_vat_lieu']})"
        else:
            don_gia = fallback
            nguon = "giá dự phòng"
        gop = don_gia * ty_le
        tong += gop
        breakdown.append({
            "thanh_phan": nhan,
            "ty_le": ty_le,
            "don_gia_vnd_kg": don_gia,
            "thanh_tien_vnd_kg": gop,
            "nguon": nguon,
        })
    return tong, breakdown


def compute_cost(conn) -> tuple:
    """Trả về (gia_thanh_vnd_per_kg, breakdown). breakdown: list dòng chi tiết."""
    import db
    fx = db.get_fx_rates(conn)
    latest = db.latest_prices_all(conn)

    # Cảnh báo nếu tổng tỷ lệ công thức lệch xa 100%
    tong_ty_le = sum(_recipe_row(e)[2] for e in RECIPE)
    if abs(tong_ty_le - 1.0) > 0.001:
        print(f"[costing][CẢNH BÁO] Tổng tỷ lệ RECIPE = {tong_ty_le:.3f} (nên = 1.0)")

    # Quy đổi sẵn về VND/kg (bỏ chỉ báo vĩ mô / tỷ giá)
    normalized = []
    for row in latest:
        if row.get("nhom") in _EXCLUDE_GROUPS:
            continue
        vnd, ok = to_vnd_per_kg(row["gia"], row["don_vi"], fx)
        if ok:
            normalized.append({**row, "vnd_per_kg": vnd})

    return cost_from_normalized(normalized, RECIPE)


def compute_and_store(conn) -> tuple:
    import db
    tong, breakdown = compute_cost(conn)
    db.insert_price(
        conn,
        {
            "ten_vat_lieu": COST_LABEL,
            "nhom": "gia_thanh",
            "gia": round(tong, 2),
            "don_vi": "VND/kg",
            "nha_cung_cap": "công thức",
            "ngay_bao_gia": None,
        },
        nguon_url="(tính toán nội bộ)",
    )
    return tong, breakdown


def format_breakdown(tong: float, breakdown: list) -> str:
    lines = ["Giá thành masterbatch theo công thức:"]
    for b in breakdown:
        lines.append(
            f"  - {b['thanh_phan']:<22} {b['ty_le']*100:>5.1f}%  "
            f"x {b['don_gia_vnd_kg']:>12,.0f} = {b['thanh_tien_vnd_kg']:>12,.0f} VND/kg  "
            f"[{b['nguon']}]"
        )
    lines.append(f"  => TỔNG: {tong:,.0f} VND/kg")
    return "\n".join(lines)


if __name__ == "__main__":
    import db
    from dotenv import load_dotenv
    load_dotenv()
    conn = db.connect()
    db.init_db(conn)
    tong, bd = compute_cost(conn)
    print(format_breakdown(tong, bd))
    conn.close()
