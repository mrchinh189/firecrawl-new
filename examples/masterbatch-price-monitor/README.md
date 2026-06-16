# Theo dõi giá NVL & phụ gia — Filler Masterbatch 🔥

Bộ công cụ dùng **Firecrawl** để cào, bóc tách và theo dõi giá nguyên vật liệu
sản xuất hạt nhựa độn (filler masterbatch): **CaCO₃ (bột đá)**, hạt nhựa nền
(**LLDPE/HDPE/PP**), **axit stearic**, **chất phủ bề mặt**, **dầu trắng**...

Tính năng:
- ✅ **Batch scrape** — cào hàng loạt URL bảng giá trong 1 job (`json` format + schema)
- ✅ **changeTracking** — chỉ xử lý khi bảng giá thực sự đổi → tiết kiệm credit, giảm nhiễu
- ✅ **Nguồn API trực tiếp** — FRED, EIA, Sina/DCE (không qua Firecrawl)
- ✅ **Tỷ giá** Vietcombank (USD/EUR/CNY)
- ✅ Lưu **lịch sử giá** vào PostgreSQL
- ✅ Vẽ **biểu đồ xu hướng** giá theo thời gian
- ✅ **Cảnh báo Telegram/Email** khi giá biến động vượt ngưỡng %

### Nguồn dữ liệu đã tích hợp

| Loại | Nguồn | Cách lấy |
|------|-------|----------|
| Web | **businessanalytiq** (14 chỉ số: PP, PE, HDPE, LDPE, LLDPE, ABS, PVC, PET, stearic acid, paraffin wax, carbon black, naphtha, ethylene, propylene) | Firecrawl batch scrape |
| Web | **ThePlasticsExchange**, **MPOC** (dầu cọ) | Firecrawl batch scrape |
| Web | **Vietcombank** (tỷ giá) | Firecrawl scrape (schema FX) |
| API | **FRED** (dầu WTI/Brent...) | HTTP trực tiếp (cần `FRED_API_KEY`) |
| API | **EIA v2** (giá dầu giao ngay) | HTTP trực tiếp (cần `EIA_API_KEY`) |
| API | **Sina/DCE** (PP, LLDPE kỳ hạn) | HTTP trực tiếp (cần Referer) |
| API | **UN Comtrade** (tùy chọn, tắt mặc định) | HTTP trực tiếp |

> ❌ **Không dùng** (paywall/chặn bot): SunSirs/SCI99, ECHEMI, Investing FCPO, LME.

---

## 1. Yêu cầu

- Firecrawl đang chạy (self-host `http://localhost:3002`, hoặc dùng cloud).
- PostgreSQL (có sẵn trong `docker-compose.yaml` của Firecrawl).
- Python 3.10+.
- Để dùng `/extract` (bóc giá bằng AI): set `OPENAI_API_KEY` trong `.env`
  **của Firecrawl** (thư mục gốc repo), hoặc cấu hình Ollama.

> ⚠️ Bản **self-host không có Fire-engine**. Các sàn chống bot mạnh
> (Alibaba, Made-in-China) có thể bị chặn → nên dùng **Firecrawl cloud**
> hoặc khai báo `PROXY_SERVER` trong `.env` của Firecrawl cho các nguồn này.

## 2. Cài đặt

```bash
cd examples/masterbatch-price-monitor
pip install -r requirements.txt
cp .env.example .env      # rồi điền thông tin của bạn
```

## 3. Cấu hình nguồn giá

Mở `config.py` và điền:
- `WEB_PRICE_URLS`: URL trang giá cào bằng Firecrawl (đã điền sẵn businessanalytiq, TPE, MPOC).
- `FX_URLS`: trang tỷ giá (đã điền sẵn Vietcombank).
- `FRED_SERIES` / `EIA_REQUESTS` / `SINA_SYMBOLS`: nguồn API trực tiếp.
- `EXTRACT_PROMPT`: tinh chỉnh mô tả dữ liệu cần bóc (đã viết sẵn cho ngành nhựa).
- `CHANGE_TRACKING_TAG`: nhãn để Firecrawl so sánh giữa các lần cào.
- `STORE_UNCHANGED`: `False` để bỏ qua trang không đổi (gọn DB), `True` để luôn lưu.

Điền key trong `.env`: `FRED_API_KEY`, `EIA_API_KEY` (và `COMTRADE_PRIMARY_KEY` nếu bật Comtrade).

> ⚠️ **Sina/DCE**: layout trường giá của futures nội địa (`nf_`) có thể đổi. Nếu giá
> lấy về sai, chỉnh chỉ số trường trong `SINA_SYMBOLS` (tham số cuối mỗi mã).

> **changeTracking hoạt động thế nào:** Firecrawl ghi nhớ lần cào trước theo `tag`
> và gắn cho mỗi trang trạng thái `new` / `changed` / `same` / `removed`. Mặc định
> bộ này **bỏ qua trang `same`**, chỉ lưu & cảnh báo khi giá thực sự thay đổi.

## 4. Chạy

```bash
python monitor.py     # cào + lưu + cảnh báo + vẽ biểu đồ
python chart.py       # chỉ vẽ lại biểu đồ từ dữ liệu đã có
```

Biểu đồ xuất ra thư mục `charts/`.

## 5. Lập lịch tự động

**Windows (Task Scheduler):** tạo task chạy hằng ngày với lệnh
`python C:\duong-dan\monitor.py`.

**Linux/macOS (cron):** ví dụ chạy 8h sáng mỗi ngày:
```cron
0 8 * * * cd /path/to/masterbatch-price-monitor && python monitor.py >> monitor.log 2>&1
```

## 6. Cấu trúc

| File | Vai trò |
|------|---------|
| `config.py`  | Nguồn giá (web + API), prompt — **nơi bạn chỉnh chính** |
| `schema.py`  | Cấu trúc JSON giá & tỷ giá mà AI bóc ra |
| `scraper.py` | Firecrawl: batch scrape (json + changeTracking), FX, `/search` |
| `apis.py`    | Nguồn API trực tiếp: FRED, EIA, Sina/DCE, Comtrade |
| `db.py`      | Lưu/đọc lịch sử giá trong PostgreSQL |
| `alerts.py`  | Gửi cảnh báo Telegram + Email |
| `chart.py`   | Vẽ biểu đồ xu hướng giá |
| `monitor.py` | Điều phối toàn bộ quy trình |

## 7. Gợi ý mở rộng

- **Giá vốn theo công thức:** ghép giá NVL với tỉ lệ phối trộn (vd 80% CaCO₃ +
  18% PE + 2% phụ gia) để tính giá thành masterbatch theo thời gian thực.
- **So sánh nhà cung cấp:** cùng một mặt hàng, xếp hạng NCC rẻ nhất.
- **Gắn tỷ giá / giá dầu thô** để dự báo xu hướng.
