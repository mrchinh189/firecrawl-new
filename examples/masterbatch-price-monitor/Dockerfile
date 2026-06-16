FROM python:3.12-slim

WORKDIR /app

# Cài thư viện trước để tận dụng cache layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn
COPY . .

RUN chmod +x entrypoint.sh

# Mặc định chạy scheduler (lặp lại theo RUN_INTERVAL_HOURS)
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["scheduler"]
