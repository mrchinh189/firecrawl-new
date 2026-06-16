"""Dashboard trực quan đọc từ Postgres. Chạy: streamlit run dashboard.py

Hiển thị: nguồn rẻ nhất (VND/kg), xu hướng giá từng mặt hàng, giá thành
masterbatch theo thời gian, và dự báo sớm naphtha -> resin.
"""

import pandas as pd
import streamlit as st

import db
from normalize import to_vnd_per_kg
from report import cheapest_by_material
from costing import compute_cost, format_breakdown
from forecast import run_forecast, format_forecast
from config import COST_LABEL


@st.cache_resource
def _conn():
    return db.connect()


def main():
    st.set_page_config(page_title="Giá NVL Masterbatch", layout="wide")
    st.title("🔥 Theo dõi giá NVL & giá thành Filler Masterbatch")

    conn = _conn()
    db.init_db(conn)

    # --- Nguồn rẻ nhất (VND/kg) ---
    st.header("Nguồn rẻ nhất (quy đổi VND/kg)")
    cheapest = cheapest_by_material(conn)
    if cheapest:
        df = pd.DataFrame(cheapest)[
            ["ten_vat_lieu", "nhom", "gia", "don_vi", "vnd_per_kg", "nha_cung_cap"]
        ].rename(columns={
            "ten_vat_lieu": "Mặt hàng", "nhom": "Nhóm", "gia": "Giá gốc",
            "don_vi": "Đơn vị", "vnd_per_kg": "VND/kg", "nha_cung_cap": "Nguồn",
        })
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu giá. Hãy chạy `python monitor.py` trước.")

    # --- Giá thành masterbatch ---
    st.header("Giá thành masterbatch")
    try:
        tong, bd = compute_cost(conn)
        st.metric("Giá thành ước tính (VND/kg)", f"{tong:,.0f}")
        st.code(format_breakdown(tong, bd))
        cost_hist = db.price_history(conn, COST_LABEL)
        if len(cost_hist) >= 2:
            ch = pd.DataFrame(cost_hist).rename(columns={"captured_at": "t", "gia": "VND/kg"})
            st.line_chart(ch.set_index("t")["VND/kg"])
    except Exception as e:  # noqa: BLE001
        st.warning(f"Chưa tính được giá thành: {e}")

    # --- Xu hướng giá từng mặt hàng ---
    st.header("Xu hướng giá theo mặt hàng")
    materials = db.distinct_materials(conn)
    if materials:
        chosen = st.selectbox("Chọn mặt hàng", materials)
        hist = db.price_history(conn, chosen)
        if len(hist) >= 2:
            h = pd.DataFrame(hist).rename(columns={"captured_at": "t", "gia": "Giá"})
            st.line_chart(h.set_index("t")["Giá"])
        else:
            st.info("Cần ít nhất 2 điểm dữ liệu để vẽ xu hướng.")

    # --- Dự báo sớm ---
    st.header("Dự báo sớm (naphtha → resin, trễ ~5 tuần)")
    try:
        st.code(format_forecast(run_forecast(conn)))
    except Exception as e:  # noqa: BLE001
        st.warning(f"Chưa dự báo được: {e}")


if __name__ == "__main__":
    main()
