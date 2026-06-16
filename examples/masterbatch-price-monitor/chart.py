"""Vẽ biểu đồ xu hướng giá từ dữ liệu đã lưu trong Postgres."""

import os

import matplotlib
matplotlib.use("Agg")  # không cần màn hình
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import db


def render_charts(out_dir: str = "charts") -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    conn = db.connect()
    paths: list[str] = []
    try:
        for name in db.distinct_materials(conn):
            history = db.price_history(conn, name)
            if len(history) < 2:
                continue  # cần >=2 điểm mới vẽ được xu hướng
            xs = [row["captured_at"] for row in history]
            ys = [row["gia"] for row in history]

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(xs, ys, marker="o")
            ax.set_title(f"Xu hướng giá: {name}")
            ax.set_xlabel("Thời gian")
            ax.set_ylabel("Giá")
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            fig.autofmt_xdate()

            safe = "".join(c if c.isalnum() else "_" for c in name)[:50]
            path = os.path.join(out_dir, f"{safe}.png")
            fig.savefig(path, dpi=120, bbox_inches="tight")
            plt.close(fig)
            paths.append(path)
            print(f"[chart] {path}")
    finally:
        conn.close()
    return paths


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    render_charts()
