"""
Bộ theo dõi giá NVL & phụ gia sản xuất filler masterbatch.

Quy trình mỗi lần chạy:
  1. Tự tìm thêm nguồn giá mới qua /search (config.SEARCH_QUERIES)
  2. Cào HÀNG LOẠT (batch scrape) toàn bộ URL trong 1 job, kèm changeTracking
  3. Bỏ qua trang KHÔNG đổi (nếu STORE_UNCHANGED=False) -> tiết kiệm credit
  4. So sánh với mức giá gần nhất đã lưu -> cảnh báo nếu biến động > ngưỡng
  5. Lưu vào Postgres và vẽ lại biểu đồ xu hướng

Chạy:  python monitor.py
Lập lịch: dùng Windows Task Scheduler / cron để chạy hằng ngày.
"""

import os
from dotenv import load_dotenv

import db
from alerts import notify
from chart import render_charts
from config import PRICE_URLS, SEARCH_QUERIES, STORE_UNCHANGED
from scraper import make_client, batch_scrape_prices, discover_urls_via_search


def check_alert(conn, item: dict, nguon_url: str, threshold: float) -> None:
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
            f"Nguồn: {nguon_url}"
        )


def main() -> None:
    load_dotenv()
    threshold = float(os.getenv("ALERT_THRESHOLD_PERCENT", "5"))

    app = make_client()
    conn = db.connect()
    db.init_db(conn)

    print("=== 1) Tìm nguồn giá mới qua /search ===")
    discovered = discover_urls_via_search(app, SEARCH_QUERIES)

    all_urls = list(dict.fromkeys(list(PRICE_URLS) + discovered))
    print(f"=== 2) Batch scrape {len(all_urls)} URL (kèm changeTracking) ===")
    pages = batch_scrape_prices(app, all_urls)

    luu = bo_qua = 0
    for page in pages:
        # Bỏ qua trang không đổi để tiết kiệm và giữ DB gọn.
        if page["change_status"] == "same" and not STORE_UNCHANGED:
            bo_qua += 1
            continue
        for item in page["san_pham"]:
            check_alert(conn, item, page["url"], threshold)
            db.insert_price(conn, item, page["url"])
            luu += 1

    print(f"=== Đã lưu {luu} mục giá, bỏ qua {bo_qua} trang không đổi ===")
    conn.close()

    print("=== 3) Vẽ biểu đồ xu hướng ===")
    render_charts()

    print("Hoàn tất.")


if __name__ == "__main__":
    main()
