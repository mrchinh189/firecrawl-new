"""
Cấu hình nguồn dữ liệu giá cho filler masterbatch.

Trung tâm là CATALOG vật liệu (MATERIALS) — mỗi mã NVL khai báo nguồn giá.
Từ catalog tự suy ra: URL businessanalytiq, mã Sina/DCE, danh sách cào web...
Mã chỉ có "NCC báo giá" -> nạp qua manual_prices.csv (nhập tay).
Feedstock (brent/naphtha/ethylene/propylene) -> chỉ báo dự báo, KHÔNG vào giá mua.

Nguồn bị paywall/chặn bot (SunSirs, ECHEMI, Investing, LME) -> KHÔNG dùng.
"""

# ===========================================================================
# CATALOG VẬT LIỆU
#   code      : mã NVL
#   ten       : tên hiển thị
#   nhom      : "resin" | "additive"
#   uu_tien   : 1 (chính) .. 3 (phụ)
#   spend     : chi tiêu (tỷ VND) — dùng để ưu tiên/đánh trọng số
#   ba        : slug businessanalytiq (None nếu không có) -> tạo URL price-index
#   sina      : mã Sina/DCE (None nếu không có)
#   tu_khoa   : từ khóa để khớp tên khi bóc dữ liệu từ trang đa-sản-phẩm (TPE...)
# ===========================================================================
MATERIALS = [
    # --- PE (Polyethylene) ---
    dict(code="lldpe", ten="LLDPE (Film Grade)", nhom="resin", uu_tien=1, spend=750,
         ba="lldpe", sina="nf_L0", tu_khoa=["lldpe"]),
    dict(code="hdpe", ten="HDPE", nhom="resin", uu_tien=1, spend=25,
         ba="hdpe", sina=None, tu_khoa=["hdpe"]),
    dict(code="ldpe", ten="LDPE", nhom="resin", uu_tien=1, spend=0,
         ba="ldpe", sina=None, tu_khoa=["ldpe"]),
    dict(code="mlldpe", ten="mLLDPE (metallocene)", nhom="resin", uu_tien=2, spend=0,
         ba="mlldpe", sina=None, tu_khoa=["mlldpe", "metallocene"]),
    dict(code="vistamaxx", ten="Vistamaxx (PBE)", nhom="resin", uu_tien=3, spend=0,
         ba=None, sina=None, tu_khoa=["vistamaxx", "pbe"]),
    # --- PP ---
    dict(code="pp", ten="PP", nhom="resin", uu_tien=1, spend=690,
         ba="polypropylene", sina="nf_PP0", tu_khoa=["pp", "polypropylene"]),
    # --- Nhựa kỹ thuật / chuyên dụng ---
    dict(code="ps", ten="PS (GPPS/HIPS)", nhom="resin", uu_tien=2, spend=11,
         ba=None, sina=None, tu_khoa=["gpps", "hips", "polystyrene", "ps "]),
    dict(code="abs", ten="ABS", nhom="resin", uu_tien=2, spend=0,
         ba="abs", sina=None, tu_khoa=["abs"]),
    dict(code="pvc", ten="PVC", nhom="resin", uu_tien=2, spend=0,
         ba="pvc", sina=None, tu_khoa=["pvc"]),
    dict(code="pet", ten="PET", nhom="resin", uu_tien=2, spend=0,
         ba="pet", sina=None, tu_khoa=["pet"]),
    dict(code="pa", ten="PA (Nylon)", nhom="resin", uu_tien=2, spend=0,
         ba=None, sina=None, tu_khoa=["nylon", "polyamide", "pa6", "pa66"]),
    dict(code="pc", ten="PC (Polycarbonate)", nhom="resin", uu_tien=2, spend=0,
         ba=None, sina=None, tu_khoa=["polycarbonate", "pc "]),
    dict(code="eva", ten="EVA", nhom="resin", uu_tien=2, spend=0,
         ba=None, sina=None, tu_khoa=["eva"]),
    dict(code="bio", ten="Nhựa Bio (PLA/PBAT)", nhom="resin", uu_tien=3, spend=0,
         ba=None, sina=None, tu_khoa=["pla", "pbat", "bio"]),
    dict(code="tpe", ten="TPE/TPU", nhom="resin", uu_tien=3, spend=0,
         ba=None, sina=None, tu_khoa=["tpe", "tpu"]),

    # --- Phụ gia chính ---
    dict(code="pe_wax", ten="PE wax", nhom="additive", uu_tien=1, spend=187,
         ba="pe-wax", sina=None, tu_khoa=["pe wax", "polyethylene wax"]),
    dict(code="stearic", ten="Stearic acid", nhom="additive", uu_tien=1, spend=132,
         ba="stearic-acid", sina=None, tu_khoa=["stearic acid"]),
    dict(code="zinc_st", ten="Zinc stearate", nhom="additive", uu_tien=1, spend=121,
         ba="zinc-stearate", sina=None, tu_khoa=["zinc stearate"]),
    dict(code="tio2", ten="TiO2 (Rutile)", nhom="additive", uu_tien=1, spend=61,
         ba="titanium-dioxide", sina=None, tu_khoa=["tio2", "titanium dioxide", "rutile"]),
    # --- Phụ gia khác ---
    dict(code="base_oil", ten="Base/Paraffin oil", nhom="additive", uu_tien=2, spend=370,
         ba="paraffin-wax", sina=None, tu_khoa=["base oil", "paraffin"]),
    dict(code="uv", ten="UV stabilizer", nhom="additive", uu_tien=3, spend=18,
         ba=None, sina=None, tu_khoa=["uv stabilizer", "uv "]),
    dict(code="fr", ten="Flame retardant", nhom="additive", uu_tien=3, spend=9,
         ba=None, sina=None, tu_khoa=["flame retardant"]),
    dict(code="ca_st", ten="Calcium stearate", nhom="additive", uu_tien=3, spend=7,
         ba=None, sina=None, tu_khoa=["calcium stearate"]),
    dict(code="coupling", ten="Coupling agent", nhom="additive", uu_tien=3, spend=5,
         ba=None, sina=None, tu_khoa=["coupling agent", "silane"]),
    # Maleic anhydride: gốc phổ biến của coupling agent (MAH-grafted) — dùng làm chỉ báo giá.
    dict(code="maleic", ten="Maleic anhydride (gốc coupling)", nhom="additive", uu_tien=3, spend=0,
         ba="maleic-anhydride", sina=None, tu_khoa=["maleic anhydride", "maleic"]),
]

# Feedstock — CHỈ BÁO dự báo (chuỗi dầu->naphtha->monomer->resin, trễ ~5 tuần).
# Không vào bảng giá mua. brent lấy từ FRED/EIA; còn lại từ businessanalytiq.
FEEDSTOCK = [
    dict(code="naphtha", ten="Naphtha", ba="naphtha"),
    dict(code="ethylene", ten="Ethylene", ba="ethylene"),
    dict(code="propylene", ten="Propylene", ba="propylene"),
    # brent: xem FRED_SERIES / EIA_REQUESTS
]

# ⚠️ Một số slug businessanalytiq là PHỎNG ĐOÁN, hãy mở URL để xác minh:
#   pe-wax, zinc-stearate, titanium-dioxide, paraffin-wax (base oil).
# Nếu sai, sửa trường "ba" của mã tương ứng ở trên. Slug sai chỉ -> không có dữ
# liệu cho mã đó (không làm hỏng lần chạy).


# ===========================================================================
# A) NGUỒN WEB — cào bằng Firecrawl (json + changeTracking)
# ===========================================================================
_BA_BASE = "https://www.businessanalytiq.com/procurementanalytics/index/"


def _ba_url(slug: str) -> str:
    return f"{_BA_BASE}{slug}-price-index/"


# Tự suy URL businessanalytiq từ catalog + feedstock
_ba_slugs = [m["ba"] for m in MATERIALS if m.get("ba")] + [f["ba"] for f in FEEDSTOCK if f.get("ba")]

# Nguồn cập nhật hằng ngày, self-host thường cào được (Tier 1-2).
WEB_SOURCES_FRESH = [
    "https://www.theplasticsexchange.com/",                       # giá spot PE/PP/PS/PVC/PET (Mỹ)
    "https://www.mpoc.org.my/market-insight/daily-palm-oil-prices/",  # dầu cọ (nền stearic)
    "https://plastic4trade.com/todays-latest-polymer-news-price-update",  # HDPE/LDPE/PP/PVC
    "https://baobianhsang.vn/gia-hat-nhua-nguyen-sinh",           # giá hạt nhựa VN (ngày)
    "https://baobianhsang.vn/gia-hat-nhua-pa",                    # PA66 VN (ngày)
    "https://www.plas.com/news/details/1604",                     # giá TQ theo ngày (bài mẫu)
    "https://www.polymerupdate.com/News/Details/1445452",         # LDPE/PE châu Á (bài mẫu)
]

WEB_PRICE_URLS = [_ba_url(s) for s in dict.fromkeys(_ba_slugs)] + WEB_SOURCES_FRESH

# Nguồn chống bot mạnh — cần Firecrawl cloud hoặc proxy (cào ở batch riêng).
# Trên self-host không proxy, các URL này thường fail (non-fatal, bỏ qua).
WEB_PRICE_URLS_ANTIBOT = [
    "https://tradingeconomics.com/commodity/naphtha",             # naphtha ~real-time
    "https://www.made-in-china.com/products-search/hot-china-products/Flame_Retardant_Additive_Price.html",
    "https://www.made-in-china.com/products-search/hot-china-products/Calcium_Stearate_Price.html",
    "https://www.made-in-china.com/products-search/hot-china-products/Paraffin_Oil_Price.html",
    "https://www.made-in-china.com/products-search/hot-china-products/Uv_Stabilizer_P_Price.html",
    "https://www.made-in-china.com/products-search/hot-china-products/Silane_Coupling_Agent_Price.html",
]
# Chế độ proxy cho nhóm chống bot (yêu cầu Fire-engine/cloud). "auto" | "stealth" | "basic".
ANTIBOT_PROXY = "auto"

# Trang tỷ giá (schema FX riêng) — Vietcombank
FX_URLS = [
    "https://portal.vietcombank.com.vn/Personal/TG/Pages/ty-gia.aspx",
]

# (Tùy chọn) tự tìm nguồn mới qua /search. Để rỗng nếu chỉ dùng nguồn cố định.
SEARCH_QUERIES: list[str] = []
SEARCH_LIMIT = 5

CHANGE_TRACKING_TAG = "masterbatch-prices"
STORE_UNCHANGED = False

# Danh sách tên mục tiêu để nhắc AI bóc đúng trên trang đa-sản-phẩm
_TARGET_NAMES = ", ".join(m["ten"] for m in MATERIALS) + \
    ", " + ", ".join(f["ten"] for f in FEEDSTOCK)

EXTRACT_PROMPT = (
    "Đây là trang về giá nguyên vật liệu ngành nhựa / phụ gia masterbatch. "
    "Hãy lấy MỌI mức giá hoặc chỉ số giá (price index) cho các mặt hàng sau nếu có: "
    f"{_TARGET_NAMES}. "
    "Với mỗi mục lấy: tên, nhóm vật liệu, mức giá (số mới nhất), đơn vị tính "
    "(USD/MT, USD/kg, cents/lb, RM/tonne, CNY/tấn...), nguồn và ngày nếu có. "
    "Bỏ qua mục không có giá."
)

FX_EXTRACT_PROMPT = (
    "Đây là bảng tỷ giá ngoại tệ của ngân hàng. Lấy tỷ giá USD, EUR, CNY gồm: "
    "mã tiền tệ, giá mua tiền mặt, giá mua chuyển khoản, giá bán. Đơn vị VND."
)


# ===========================================================================
# B) NGUỒN API TRỰC TIẾP — gọi HTTP, không qua Firecrawl
# ===========================================================================

# --- FRED --- (series_id, tên, đơn vị, nhóm)
FRED_SERIES = [
    ("DCOILWTICO",   "Dầu thô WTI",   "USD/thùng", "chi_so_vimo"),
    ("DCOILBRENTEU", "Dầu thô Brent", "USD/thùng", "chi_so_vimo"),
]

# --- EIA v2 petroleum spot --- (tên, đơn vị, nhóm, params bổ sung)
EIA_REQUESTS = [
    ("Dầu WTI Cushing (EIA)", "USD/thùng", "chi_so_vimo", {"facets[series][]": "RWTC"}),
    ("Dầu Brent (EIA)",       "USD/thùng", "chi_so_vimo", {"facets[series][]": "RBRTE"}),
]
EIA_BASE = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

# --- Sina/DCE --- tự suy từ catalog: mã -> (tên, nhóm, đơn vị, chỉ số trường giá)
SINA_SYMBOLS = {
    m["sina"]: (f"{m['ten']} (DCE)", "resin", "CNY/tấn", 8)
    for m in MATERIALS if m.get("sina")
}
SINA_URL = "https://hq.sinajs.cn/list="
SINA_REFERER = "https://finance.sina.com.cn"

# --- UN Comtrade (tùy chọn, mặc định TẮT) ---
COMTRADE_REQUESTS: list[dict] = []


# ===========================================================================
# C) NHẬP TAY — báo giá NCC cho mã không có nguồn web tự động
# ===========================================================================
# File CSV cột: code,gia,don_vi,nha_cung_cap,ngay  (xem manual_prices.example.csv)
MANUAL_PRICES_CSV = "manual_prices.csv"


# ===========================================================================
# D) QUY ĐỔI & TÍNH GIÁ THÀNH
# ===========================================================================
# Tỷ giá dự phòng (VND/1 đơn vị tiền) — dùng khi chưa lấy được từ Vietcombank.
FX_FALLBACK = {"USD": 25400.0, "EUR": 27500.0, "CNY": 3500.0, "MYR": 5400.0}

# Công thức phối trộn (tỷ lệ khối lượng). CHỈNH theo công thức thực tế của bạn.
# (nhãn, [từ khóa khớp], tỷ lệ, giá dự phòng VND/kg, [từ khóa LOẠI TRỪ] (tùy chọn))
# exclude giúp tránh khớp nhầm, vd "polyethylene" của hạt nhựa nền không bắt "polyethylene wax".
RECIPE = [
    ("Bột đá CaCO3", ["caco3", "calcium carbonate", "bột đá", "carbonate"], 0.80, 2500.0, []),
    ("Hạt nhựa nền PE (LLDPE)", ["lldpe", "ldpe", "hdpe", "polyethylene"], 0.18, 32000.0, ["wax"]),
    ("Phụ gia (stearic/PE wax)", ["stearic", "pe wax", "polyethylene wax"], 0.02, 35000.0, []),
]
COST_LABEL = "Giá thành masterbatch (công thức)"


# ===========================================================================
# E) DỰ BÁO — chuỗi dẫn dắt dầu/naphtha -> resin (trễ ~5 tuần)
# ===========================================================================
# Mỗi mục: (tên chỉ báo dẫn dắt trong DB, [từ khóa resin mục tiêu], độ trễ tuần,
#           độ co giãn beta = %resin thay đổi cho mỗi 1% chỉ báo thay đổi).
# beta=None -> tự ước lượng bằng hồi quy nếu đủ dữ liệu, ngược lại dùng BETA_FALLBACK.
FORECAST = [
    ("Naphtha", ["pp", "polypropylene"], 5, None),
    ("Naphtha", ["lldpe", "ldpe", "hdpe", "polyethylene"], 5, None),
]
FORECAST_BETA_FALLBACK = 0.6   # co giãn mặc định khi thiếu dữ liệu hồi quy
FORECAST_LOOKBACK_WEEKS = 4    # so sánh thay đổi chỉ báo trong N tuần gần nhất
FORECAST_ALERT_PERCENT = 5     # cảnh báo sớm nếu dự báo resin biến động >= %
