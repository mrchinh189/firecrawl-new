# Theo dõi giá nguyên vật liệu (NVL) với Firecrawl

Công cụ cào giá NVL hằng ngày bằng **Firecrawl self-host**, lưu lịch sử vào **Google Sheets** và gửi **cảnh báo** (Telegram / email) khi giá biến động vượt ngưỡng.

```
cron (hằng ngày) ─► nvl_tracker ─► Firecrawl /v2/scrape (self-host) ─► parser theo từng nguồn
                                                                          │
                       Google Sheets ◄── lưu lịch sử + bảng giá mới nhất ◄─┤
                       Telegram / Email ◄── cảnh báo khi |%Δ| ≥ ngưỡng ◄───┘
```

## Nguồn đang cấu hình (`sources.yaml`)

| Mã | NVL | Nguồn | Cách lấy | Đơn vị |
|---|---|---|---|---|
| `CPO_INVESTING` | Dầu cọ thô Malaysia (CPOc1) | vn.investing.com | metadata JSON của trang (`LAST_PRICE`), dự phòng đọc markdown | USD/tấn |
| `CPO_MPOC` | Dầu cọ thô CPO (Bursa) | mpoc.org.my | bảng *CPO Prices* (10 phiên gần nhất) | RM/tấn |
| `H2SO4_100PPI` | Axit sulfuric 硫酸 | 100ppi.com (生意社) | bảng 日期/价格 (8 phiên gần nhất) | CNY/tấn |
| `ZINC_LME_CASH`, `ZINC_LME_3_MONTH` | Kẽm LME | lme.com | API JSON mà trang LME Zinc dùng để hiển thị *Official Prices* (giá Offer) | USD/tấn |

Các parser là **cố định (không cần LLM)**: chạy nhanh, không tốn chi phí AI và cho kết quả ổn định. Mỗi nguồn được cào qua Firecrawl với `maxAge: 0` để luôn lấy giá mới, không lấy bản cache.

> **Lưu ý LME:** trang `https://www.lme.com/en/Metals/Non-ferrous/LME-Zinc` tải bảng giá bằng JavaScript, nên cào trang HTML sẽ không thấy số. Tool gọi thẳng API `/api/trading-data/day-delayed?datasourceId=…`. Muốn theo dõi kim loại khác (đồng, nhôm…), mở trang kim loại đó, xem source HTML, tìm thẻ `<day-delayed-data-table … datasource-id="…">` rồi thay `datasourceId`.

## 1. Chạy Firecrawl self-host

Ở thư mục gốc repo này (xem thêm [`SELF_HOST.md`](../../SELF_HOST.md)):

```bash
cp apps/api/.env.example .env      # hoặc tạo .env theo SELF_HOST.md (USE_DB_AUTHENTICATION=false)
docker compose up -d
curl -s -X POST http://localhost:3002/v2/scrape -H 'Content-Type: application/json' \
  -d '{"url":"https://www.mpoc.org.my/market-insight/daily-palm-oil-prices/"}' | head -c 300
```

## 2. Cài công cụ

```bash
cd examples/nvl-price-tracker
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env               # rồi điền các biến
.venv/bin/python -m nvl_tracker.tracker --dry-run   # chạy thử: chỉ in kết quả, không lưu, không gửi cảnh báo
```

Khi chưa đặt `GOOGLE_SHEET_ID`, dữ liệu được ghi ra CSV trong `./data/`. Cách này tiện để chạy thử trước khi nối Google Sheets.

## 3. Kết nối Google Sheets

1. Vào Google Cloud Console, tạo project và bật **Google Sheets API**.
2. Tạo **Service Account**, tạo key dạng JSON và lưu thành `service_account.json` trong thư mục này.
3. Tạo một Google Sheet, rồi **Share** cho email của service account (`…@….iam.gserviceaccount.com`) với quyền **Editor**.
4. Ghi ID của sheet (đoạn giữa `/d/` và `/edit` trong URL) vào `.env`: `GOOGLE_SHEET_ID=...`

Tool tự tạo 2 tab:

- **`LichSuGia`**: mỗi dòng là một giá (thời điểm cào, mã, tên, ngày giá, giá, đơn vị, % thay đổi so với phiên trước, ghi chú, nguồn). Tool không ghi trùng cặp *(mã, ngày giá)*, nên chạy lại nhiều lần trong ngày vẫn an toàn. Lần chạy đầu tiên tự nạp sẵn các phiên cũ mà trang đang hiển thị.
- **`GiaMoiNhat`**: mỗi mã một dòng gồm giá mới nhất, giá trước và % thay đổi. Tab này phù hợp để làm dashboard hoặc biểu đồ.

## 4. Cảnh báo

- Ngưỡng mặc định là `alert_threshold_pct: 2.0` trong `sources.yaml`. Từng nguồn có thể đặt ngưỡng riêng bằng `alert_threshold_pct`.
- Mỗi mã chỉ được so **giá mới nhất** với phiên liền trước, rồi gửi một tin tổng hợp. Tin này cũng liệt kê các **nguồn bị lỗi** (bị chặn, đổi giao diện…) để bạn biết mà xử lý.
- **Telegram:** tạo bot qua @BotFather để lấy `TELEGRAM_BOT_TOKEN`. Nhắn cho bot một tin, rồi mở `https://api.telegram.org/bot<TOKEN>/getUpdates` để lấy `TELEGRAM_CHAT_ID`.
- **Email:** điền `SMTP_*` và `ALERT_EMAIL_TO` (nhiều địa chỉ thì ngăn cách bằng dấu phẩy). Với Gmail, dùng *App Password*.

## 5. Chạy hằng ngày (cron)

```cron
# 15:30 giờ VN, thứ 2–7 (100ppi công bố giá trước ~14:00 giờ TQ; LME/Bursa chốt phiên trước đó)
30 15 * * 1-6  /đường/dẫn/firecrawl-new/examples/nvl-price-tracker/run_daily.sh
```

Đặt `TZ=Asia/Ho_Chi_Minh` trong crontab nếu server không dùng giờ VN. Log được ghi vào `logs/tracker-YYYY-MM.log`. Chương trình thoát với mã khác 0 khi **tất cả** nguồn đều lỗi.

Các tuỳ chọn dòng lệnh:

```bash
python -m nvl_tracker.tracker --only ZINC_LME CPO_MPOC   # chỉ chạy một số nguồn
python -m nvl_tracker.tracker --no-alert                 # lưu dữ liệu nhưng không gửi cảnh báo
```

## Thêm nguồn mới

- **Không muốn viết code:** dùng `parser: llm_json`. Firecrawl sẽ dùng LLM để trích `{price, price_date, unit}`. Cách này cần cấu hình `OPENAI_API_KEY` hoặc `OLLAMA_BASE_URL` trong `.env` của Firecrawl self-host. Xem ví dụ đã comment sẵn trong `sources.yaml`.
- **Muốn ổn định và miễn phí:** viết thêm hàm `parse_xxx` trong `nvl_tracker/parsers.py`, đăng ký vào `PARSERS`, rồi thêm fixture và test trong `tests/`.

## Khi bị chặn (Investing.com, Cloudflare…)

Bản self-host **không có fire-engine** (phần chống chặn bot của Firecrawl Cloud). Một số trang như Investing.com có thể thỉnh thoảng trả về trang kiểm tra bot. Khi đó tool báo lỗi `ParseError` cho nguồn đó, không ghi giá sai, và đưa nguồn vào cảnh báo. Có 3 cách xử lý:

1. Cấu hình proxy cho Firecrawl self-host: đặt `PROXY_SERVER`, `PROXY_USERNAME`, `PROXY_PASSWORD` trong `.env` gốc (nên dùng proxy dân cư).
2. Đặt `FIRECRAWL_FALLBACK_API_KEY` (key Firecrawl Cloud). Tool chỉ gọi cloud khi self-host thất bại, nên tốn rất ít credit.
3. Thêm thời gian chờ cho nguồn đó, ví dụ `scrape_options: { waitFor: 3000 }`.

## Test

```bash
.venv/bin/python -m pytest -q
```

Các test dùng nội dung thật của 4 trang, đã được Firecrawl cào ngày 04/10/2026 và lưu trong `tests/fixtures/`. Test kiểm tra parser, chống ghi trùng, cảnh báo, và trường hợp trang bị chặn.
