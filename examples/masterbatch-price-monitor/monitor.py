"""
Bộ theo dõi giá NVL & phụ gia sản xuất filler masterbatch.

Nạp dữ liệu từ 3 luồng vào cùng 1 database:
  1. WEB (Firecrawl batch scrape + changeTracking): businessanalytiq, TPE, MPOC
  2. FX (Firecrawl scrape): tỷ giá Vietcombank
  3. API trực tiếp: FRED, EIA, Sina/DCE, (Comtrade tùy chọn)

Sau đó: so ngưỡng % -> cảnh báo, lưu Postgres, vẽ biểu đồ.

Chạy:  python monitor.py
Lập lịch: Windows Task Scheduler / cron để chạy hằng ngày.
"""

import os
from dotenv import load_dotenv

import db
from alerts import notify
from chart import render_charts
from config import (
    WEB_PRICE_URLS, WEB_PRICE_URLS_ANTIBOT, ANTIBOT_PROXY,
    FX_URLS, SEARCH_QUERIES, STORE_UNCHANGED, MANUAL_PRICES_CSV,
)
from scraper import (
    make_client, batch_scrape_prices, scrape_fx, discover_urls_via_search,
)
from apis import fetch_all_apis
from manual import load_manual_prices
from costing import compute_and_store, format_breakdown
from report import export_csv, print_summary


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
            f"Giá cũ: {gia_cu:,.2f} → Giá mới: {gia_moi:,.2f} {item.get('don_vi','')}\n"
            f"Nguồn: {nguon_url}"
        )


def store_rows(conn, rows: list[dict], threshold: float) -> int:
    """Lưu danh sách dòng phẳng (FX/API) + cảnh báo. Trả về số dòng đã lưu."""
    n = 0
    for item in rows:
        nguon = item.get("_nguon_url", "")
        check_alert(conn, item, nguon, threshold)
        db.insert_price(conn, item, nguon)
        n += 1
    return n


def main() -> None:
    load_dotenv()
    threshold = float(os.getenv("ALERT_THRESHOLD_PERCENT", "5"))

    app = make_client()
    conn = db.connect()
    db.init_db(conn)

    def xu_ly_pages(pages):
        n_luu = n_bo = 0
        for page in pages:
            if page["change_status"] == "same" and not STORE_UNCHANGED:
                n_bo += 1
                continue
            for item in page["san_pham"]:
                check_alert(conn, item, page["url"], threshold)
                db.insert_price(conn, item, page["url"])
                n_luu += 1
        return n_luu, n_bo

    # --- 1) WEB: batch scrape giá NVL (kèm changeTracking) ---
    discovered = discover_urls_via_search(app, SEARCH_QUERIES) if SEARCH_QUERIES else []
    web_urls = list(dict.fromkeys(list(WEB_PRICE_URLS) + discovered))
    print(f"=== 1) Batch scrape {len(web_urls)} URL giá NVL ===")
    luu, bo_qua = xu_ly_pages(batch_scrape_prices(app, web_urls))

    # --- 1b) Nguồn chống bot (Trading Economics, Made-in-China) — batch riêng + proxy ---
    if WEB_PRICE_URLS_ANTIBOT:
        print(f"=== 1b) Batch chống bot {len(WEB_PRICE_URLS_ANTIBOT)} URL (proxy={ANTIBOT_PROXY}) ===")
        l2, b2 = xu_ly_pages(batch_scrape_prices(app, WEB_PRICE_URLS_ANTIBOT, proxy=ANTIBOT_PROXY))
        luu += l2
        bo_qua += b2

    # --- 2) FX: tỷ giá Vietcombank ---
    print("=== 2) Tỷ giá (Vietcombank) ===")
    luu += store_rows(conn, scrape_fx(app, FX_URLS), threshold)

    # --- 3) API trực tiếp: FRED / EIA / Sina / Comtrade ---
    print("=== 3) API trực tiếp (FRED/EIA/Sina/Comtrade) ===")
    luu += store_rows(conn, fetch_all_apis(), threshold)

    # --- 3b) Báo giá NCC nhập tay (mã không có nguồn web tự động) ---
    print("=== 3b) Báo giá NCC (manual_prices.csv) ===")
    luu += store_rows(conn, load_manual_prices(MANUAL_PRICES_CSV), threshold)

    print(f"=== Đã lưu {luu} mục, bỏ qua {bo_qua} trang web không đổi ===")

    # --- 4) Tính giá thành masterbatch theo công thức ---
    print("=== 4) Tính giá thành theo công thức ===")
    try:
        tong, breakdown = compute_and_store(conn)
        print(format_breakdown(tong, breakdown))
    except Exception as e:  # noqa: BLE001
        print(f"[costing][LỖI] {e}")

    # --- 5) Báo cáo nguồn rẻ nhất + xuất CSV ---
    print("=== 5) Báo cáo nguồn rẻ nhất ===")
    try:
        print_summary(conn)
        export_csv(conn)
    except Exception as e:  # noqa: BLE001
        print(f"[report][LỖI] {e}")

    # --- 5b) Dự báo sớm naphtha -> resin ---
    print("=== 5b) Dự báo sớm (naphtha -> resin) ===")
    try:
        from forecast import run_forecast, format_forecast
        print(format_forecast(run_forecast(conn)))
    except Exception as e:  # noqa: BLE001
        print(f"[forecast][LỖI] {e}")

    conn.close()

    print("=== 6) Vẽ biểu đồ xu hướng ===")
    render_charts()

    print("Hoàn tất.")


if __name__ == "__main__":
    main()
