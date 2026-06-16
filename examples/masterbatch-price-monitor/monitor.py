"""
Bộ theo dõi giá NVL & phụ gia sản xuất filler masterbatch.

Quy trình mỗi lần chạy:
  1. Cào giá từ các URL bảng giá (config.PRICE_URLS)
  2. Tự tìm nguồn giá mới qua /search (config.SEARCH_QUERIES)
  3. So sánh với mức giá gần nhất đã lưu -> cảnh báo nếu biến động > ngưỡng
  4. Lưu toàn bộ vào Postgres
  5. Vẽ lại biểu đồ xu hướng

Chạy:  python monitor.py
Lập lịch: dùng Windows Task Scheduler / cron để chạy hằng ngày.
"""

import os
from dotenv import load_dotenv

import db
from alerts import notify
from chart import render_charts
from config import PRICE_URLS, SEARCH_QUERIES
from scraper import make_client, extract_prices_from_urls, discover_via_search


def check_alert(conn, item: dict, threshold: float) -> None:
    name = item.get("ten_vat_lieu")
    gia_moi = item.get("gia")
    if not name or gia_moi is None:
        return
    prev = db.latest_price(conn, name)
    if not prev or not prev.get("gia"):
        return
    gia_cu = prev["gia"]
    if gia_cu == 0:
        return
    delta = (gia_moi - gia_cu) / gia_cu * 100
    if abs(delta) >= threshold:
        chieu = "TĂNG 📈" if delta > 0 else "GIẢM 📉"
        notify(
            f"<b>{name}</b> {chieu} {abs(delta):.1f}%\n"
            f"Giá cũ: {gia_cu:,.0f} → Giá mới: {gia_moi:,.0f} {item.get('don_vi','')}\n"
            f"Nguồn: {item.get('_nguon_url','')}"
        )


def main() -> None:
    load_dotenv()
    threshold = float(os.getenv("ALERT_THRESHOLD_PERCENT", "5"))

    app = make_client()
    conn = db.connect()
    db.init_db(conn)

    print("=== 1) Cào URL bảng giá trực tiếp ===")
    rows = extract_prices_from_urls(app, PRICE_URLS)

    print("=== 2) Tìm nguồn giá mới qua /search ===")
    rows += discover_via_search(app, SEARCH_QUERIES)

    print(f"=== Tổng cộng {len(rows)} mục giá. Đối chiếu & lưu ===")
    for item in rows:
        nguon = item.pop("_nguon_url", None)
        check_alert(conn, {**item, "_nguon_url": nguon}, threshold)
        db.insert_price(conn, item, nguon)

    conn.close()

    print("=== 3) Vẽ biểu đồ xu hướng ===")
    render_charts()

    print("Hoàn tất.")


if __name__ == "__main__":
    main()
