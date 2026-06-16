"""Dự báo sớm giá resin theo chuỗi dẫn dắt dầu thô -> naphtha -> monomer -> resin.

Nguyên lý: giá naphtha (đầu vào) biến động trước, giá hạt nhựa phản ánh sau
~5 tuần. Module ước lượng độ co giãn (beta) giữa %thay đổi naphtha và %thay đổi
resin (hồi quy đơn giản nếu đủ dữ liệu), rồi chiếu thay đổi naphtha gần đây thành
dự báo giá resin sau độ trễ.

Đây là mô hình ĐƠN GIẢN mang tính cảnh báo sớm, không phải dự báo chính xác.
"""

from datetime import timedelta

from config import (
    FORECAST, FORECAST_BETA_FALLBACK, FORECAST_LOOKBACK_WEEKS, FORECAST_ALERT_PERCENT,
)


def _series(history: list) -> list:
    """[(t, gia)] -> đã sắp xếp tăng dần theo thời gian, bỏ None."""
    s = [(h["captured_at"], h["gia"]) for h in history if h.get("gia") is not None]
    return sorted(s, key=lambda x: x[0])


def _pct_change_window(series: list, weeks: int):
    """%thay đổi giữa điểm mới nhất và điểm cách đây ~weeks tuần."""
    if len(series) < 2:
        return None
    t_now, v_now = series[-1]
    cutoff = t_now - timedelta(weeks=weeks)
    older = [v for (t, v) in series if t <= cutoff] or [series[0][1]]
    v_old = older[-1]
    if not v_old:
        return None
    return (v_now - v_old) / v_old * 100.0


def _estimate_beta(lead: list, resin: list, lag_weeks: int):
    """Hồi quy thô: %Δresin(t) ~ beta * %Δlead(t - lag). Trả None nếu thiếu dữ liệu."""
    if len(lead) < 6 or len(resin) < 6:
        return None
    # Tạo chuỗi %thay đổi theo từng mốc resin, ghép với lead trễ lag tuần.
    xs, ys = [], []
    for i in range(1, len(resin)):
        t, v = resin[i]
        v_prev = resin[i - 1][1]
        if not v_prev:
            continue
        dy = (v - v_prev) / v_prev * 100.0
        # lead tại thời điểm t - lag
        cutoff = t - timedelta(weeks=lag_weeks)
        lead_at = [lv for (lt, lv) in lead if lt <= cutoff]
        lead_before = [lv for (lt, lv) in lead if lt <= cutoff - timedelta(weeks=1)]
        if not lead_at or not lead_before or not lead_before[-1]:
            continue
        dx = (lead_at[-1] - lead_before[-1]) / lead_before[-1] * 100.0
        xs.append(dx)
        ys.append(dy)
    if len(xs) < 4:
        return None
    sxx = sum(x * x for x in xs)
    if sxx == 0:
        return None
    return sum(x * y for x, y in zip(xs, ys)) / sxx  # beta qua gốc tọa độ


def run_forecast(conn) -> list:
    """Trả về danh sách dự báo: [{lead, resin, beta, lead_change_pct,
    du_bao_pct, gia_hien_tai, gia_du_bao, lag_weeks}]. Cảnh báo nếu vượt ngưỡng."""
    import db
    from alerts import notify

    out = []
    for lead_name, resin_kw, lag_weeks, beta_cfg in FORECAST:
        lead_hist = _series(db.price_history(conn, lead_name))
        if not lead_hist:
            continue
        lead_change = _pct_change_window(lead_hist, FORECAST_LOOKBACK_WEEKS)
        if lead_change is None:
            continue

        # Resin: gộp lịch sử mọi mặt hàng khớp từ khóa
        resin_hist = []
        cur_name = cur_price = None
        for name in db.distinct_materials(conn):
            low = name.lower()
            if any(k in low for k in resin_kw) and "wax" not in low:
                h = _series(db.price_history(conn, name))
                if h:
                    resin_hist += h
                    if not cur_name or h[-1][0] > cur_price[0]:
                        cur_name, cur_price = name, h[-1]
        if not resin_hist:
            continue
        resin_hist.sort(key=lambda x: x[0])

        beta = beta_cfg if beta_cfg is not None else _estimate_beta(lead_hist, resin_hist, lag_weeks)
        if beta is None:
            beta = FORECAST_BETA_FALLBACK

        du_bao_pct = beta * lead_change
        gia_ht = cur_price[1]
        gia_db = gia_ht * (1 + du_bao_pct / 100.0)
        rec = {
            "lead": lead_name, "resin": cur_name, "beta": round(beta, 3),
            "lead_change_pct": round(lead_change, 2), "du_bao_pct": round(du_bao_pct, 2),
            "gia_hien_tai": gia_ht, "gia_du_bao": round(gia_db, 2), "lag_weeks": lag_weeks,
        }
        out.append(rec)

        if abs(du_bao_pct) >= FORECAST_ALERT_PERCENT:
            chieu = "TĂNG 📈" if du_bao_pct > 0 else "GIẢM 📉"
            notify(
                f"<b>[Dự báo sớm] {cur_name}</b> dự kiến {chieu} {abs(du_bao_pct):.1f}% "
                f"sau ~{lag_weeks} tuần\n(do {lead_name} {('+' if lead_change>=0 else '')}"
                f"{lead_change:.1f}% gần đây, beta={beta:.2f})",
                subject="Cảnh báo dự báo giá resin",
            )
    return out


def format_forecast(rows: list) -> str:
    if not rows:
        return "Dự báo: chưa đủ dữ liệu (cần thêm lịch sử naphtha & resin)."
    lines = ["Dự báo sớm giá resin (chuỗi naphtha -> resin):"]
    for r in rows:
        lines.append(
            f"  - {r['resin']:<26} dự kiến {r['du_bao_pct']:+.1f}% sau ~{r['lag_weeks']}T "
            f"({r['gia_hien_tai']:,.0f} -> {r['gia_du_bao']:,.0f}) "
            f"[{r['lead']} {r['lead_change_pct']:+.1f}%, beta={r['beta']}]"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import db
    from dotenv import load_dotenv
    load_dotenv()
    conn = db.connect()
    db.init_db(conn)
    print(format_forecast(run_forecast(conn)))
    conn.close()
