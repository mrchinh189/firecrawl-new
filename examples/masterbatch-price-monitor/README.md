# Theo dõi giá NVL & phụ gia — Filler Masterbatch 🔥

Bộ công cụ dùng **Firecrawl** để cào, bóc tách và theo dõi giá nguyên vật liệu
sản xuất hạt nhựa độn (filler masterbatch): **CaCO₃ (bột đá)**, hạt nhựa nền
(**LLDPE/HDPE/PP**), **axit stearic**, **chất phủ bề mặt**, **dầu trắng**...

Tính năng:
- ✅ **Batch scrape** — cào hàng loạt URL bảng giá trong 1 job (`json` format + schema)
- ✅ **changeTracking** — chỉ xử lý khi bảng giá thực sự đổi → tiết kiệm credit, giảm nhiễu
- ✅ Tự tìm nguồn giá mới trên web (`/search`)
- ✅ Lưu **lịch sử giá** vào PostgreSQL
- ✅ Vẽ **biểu đồ xu hướng** giá theo thời gian
- ✅ **Cảnh báo Telegram/Email** khi giá biến động vượt ngưỡng %

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
- `PRICE_URLS`: các URL bảng giá muốn cào trực tiếp.
- `SEARCH_QUERIES`: từ khóa để tự tìm nguồn giá mới.
- `EXTRACT_PROMPT`: tinh chỉnh mô tả dữ liệu cần bóc (đã viết sẵn cho masterbatch).
- `CHANGE_TRACKING_TAG`: nhãn để Firecrawl so sánh giữa các lần cào.
- `STORE_UNCHANGED`: `False` để bỏ qua trang không đổi (gọn DB), `True` để luôn lưu.

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
| `config.py`  | Nguồn giá, từ khóa, prompt — **nơi bạn chỉnh chính** |
| `schema.py`  | Cấu trúc JSON giá mà AI bóc ra |
| `scraper.py` | Batch scrape (json + changeTracking) và `/search` |
| `db.py`      | Lưu/đọc lịch sử giá trong PostgreSQL |
| `alerts.py`  | Gửi cảnh báo Telegram + Email |
| `chart.py`   | Vẽ biểu đồ xu hướng giá |
| `monitor.py` | Điều phối toàn bộ quy trình |

## 7. Gợi ý mở rộng

- **Giá vốn theo công thức:** ghép giá NVL với tỉ lệ phối trộn (vd 80% CaCO₃ +
  18% PE + 2% phụ gia) để tính giá thành masterbatch theo thời gian thực.
- **So sánh nhà cung cấp:** cùng một mặt hàng, xếp hạng NCC rẻ nhất.
- **Gắn tỷ giá / giá dầu thô** để dự báo xu hướng.
