#!/bin/sh
# Điểm vào container — chọn chế độ qua tham số đầu tiên.
set -e

case "$1" in
  dashboard)
    exec streamlit run dashboard.py \
      --server.address=0.0.0.0 --server.port="${DASHBOARD_PORT:-8501}"
    ;;
  monitor-once)
    exec python monitor.py
    ;;
  scheduler)
    INTERVAL="${RUN_INTERVAL_HOURS:-24}"
    echo "[scheduler] chạy monitor mỗi ${INTERVAL} giờ"
    while true; do
      echo "[scheduler] $(date -u) bắt đầu chạy monitor.py"
      python monitor.py || echo "[scheduler] monitor.py lỗi, tiếp tục chờ chu kỳ sau"
      sleep $((INTERVAL * 3600))
    done
    ;;
  *)
    exec "$@"
    ;;
esac
