"""Báo cáo tổng hợp: nguồn rẻ nhất cho từng mặt hàng + xuất CSV.

Quy đổi mọi giá về VND/kg để so sánh công bằng giữa các nguồn/đơn vị khác nhau.
"""

import csv
import os
from datetime import datetime

import db
from normalize import to_vnd_per_kg


def cheapest_by_material(conn) -> list:
    """Với mỗi mặt hàng, tìm nguồn có giá (đã quy đổi VND/kg) rẻ nhất."""
    fx = db.get_fx_rates(conn)
    rows = db.latest_prices_all(conn)

    best: dict = {}
    for r in rows:
        vnd, ok = to_vnd_per_kg(r["gia"], r["don_vi"], fx)
        if not ok:
            continue
        key = r["ten_vat_lieu"].lower().strip()
        if key not in best or vnd < best[key]["vnd_per_kg"]:
            best[key] = {**r, "vnd_per_kg": vnd}
    return sorted(best.values(), key=lambda x: x["vnd_per_kg"])


def export_csv(conn, out_dir: str = "reports") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"gia_{datetime.now():%Y%m%d}.csv")
    rows = cheapest_by_material(conn)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Mặt hàng", "Nhóm", "Giá gốc", "Đơn vị", "Giá quy đổi (VND/kg)", "Nguồn"])
        for r in rows:
            w.writerow([
                r["ten_vat_lieu"], r["nhom"], r["gia"], r["don_vi"],
                round(r["vnd_per_kg"], 2), r["nha_cung_cap"],
            ])
    print(f"[report] {path} ({len(rows)} mặt hàng)")
    return path


def print_summary(conn) -> None:
    rows = cheapest_by_material(conn)
    print("\n=== NGUỒN RẺ NHẤT (quy đổi VND/kg) ===")
    for r in rows[:30]:
        print(f"  {r['ten_vat_lieu']:<34} {r['vnd_per_kg']:>12,.0f} VND/kg  "
              f"[{r['nha_cung_cap']}]")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    conn = db.connect()
    db.init_db(conn)
    print_summary(conn)
    export_csv(conn)
    conn.close()
