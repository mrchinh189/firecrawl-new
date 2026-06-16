"""
Cấu hình nguồn dữ liệu giá cho filler masterbatch.

Có 2 luồng nạp dữ liệu:
  A. WEB (Firecrawl scrape)  -> WEB_PRICE_URLS, FX_URLS
  B. API trực tiếp (HTTP)    -> FRED_SERIES, EIA_REQUESTS, SINA_SYMBOLS, COMTRADE_REQUESTS

Sửa file này để thêm/bớt nguồn. Không cần đụng code logic.
Nguồn bị paywall/chặn bot (SunSirs, ECHEMI, Investing, LME) -> KHÔNG dùng.
"""

# ===========================================================================
# A) NGUỒN WEB — cào bằng Firecrawl (json + changeTracking)
# ===========================================================================

_BA = "https://www.businessanalytiq.com/procurementanalytics/index/"
_BA_SLUGS = [
    "polypropylene", "polyethylene", "hdpe", "ldpe", "lldpe",
    "abs", "pvc", "pet", "stearic-acid", "paraffin-wax",
    "carbon-black", "naphtha", "ethylene", "propylene",
]

WEB_PRICE_URLS = [f"{_BA}{slug}-price-index/" for slug in _BA_SLUGS] + [
    "https://www.theplasticsexchange.com/",
    "https://www.mpoc.org.my/market-insight/daily-palm-oil-prices/",
]

# Trang tỷ giá (bóc bằng schema FX riêng) — Vietcombank
FX_URLS = [
    "https://portal.vietcombank.com.vn/Personal/TG/Pages/ty-gia.aspx",
]

# (Tùy chọn) Tự tìm thêm nguồn giá mới qua /search. Để rỗng nếu chỉ dùng nguồn cố định.
SEARCH_QUERIES: list[str] = []
SEARCH_LIMIT = 5

# changeTracking: Firecrawl ghi nhớ lần cào trước theo "tag" và báo new/changed/same/removed.
CHANGE_TRACKING_TAG = "masterbatch-prices"
# Lưu cả khi trang KHÔNG đổi? False = bỏ qua trang "same" (gọn DB, tiết kiệm credit).
STORE_UNCHANGED = False

EXTRACT_PROMPT = (
    "Đây là trang về giá nguyên vật liệu / phụ gia ngành nhựa và filler masterbatch. "
    "Hãy lấy MỌI mức giá hoặc chỉ số giá (price index) tìm được cho: hạt nhựa "
    "(PP, PE, HDPE, LDPE, LLDPE, ABS, PVC, PET), naphtha, ethylene, propylene, "
    "axit stearic (stearic acid), paraffin wax, carbon black, dầu cọ (palm oil). "
    "Với mỗi mục lấy: tên, nhóm vật liệu, mức giá (số mới nhất), đơn vị tính "
    "(USD/MT, USD/kg, cents/lb, RM/tonne, CNY/tấn...), nguồn và ngày nếu có. "
    "Bỏ qua mục không có giá."
)

FX_EXTRACT_PROMPT = (
    "Đây là bảng tỷ giá ngoại tệ của ngân hàng. Lấy tỷ giá các đồng tiền chính "
    "(USD, EUR, CNY) gồm: mã tiền tệ, giá mua tiền mặt, giá mua chuyển khoản, "
    "giá bán. Đơn vị VND."
)

# ===========================================================================
# B) NGUỒN API TRỰC TIẾP — gọi HTTP, không qua Firecrawl
#    Key lấy từ biến môi trường trong .env (xem .env.example).
# ===========================================================================

# --- FRED (Federal Reserve Economic Data) ---------------------------------
# Mỗi mục: (series_id, tên hiển thị, đơn vị, nhóm)
FRED_SERIES = [
    ("DCOILWTICO",  "Dầu thô WTI",   "USD/thùng", "chi_so_vimo"),
    ("DCOILBRENTEU", "Dầu thô Brent", "USD/thùng", "chi_so_vimo"),
    # Thêm series khác sau khi tra ở /fred/series/search, ví dụ giá nhựa PPI...
]

# --- EIA v2 (petroleum spot prices) ---------------------------------------
# Mỗi mục: (tên hiển thị, đơn vị, nhóm, dict params bổ sung cho /v2/petroleum/pri/spt/data/)
EIA_REQUESTS = [
    ("Dầu WTI Cushing (EIA)", "USD/thùng", "chi_so_vimo", {"facets[series][]": "RWTC"}),
    ("Dầu Brent (EIA)",       "USD/thùng", "chi_so_vimo", {"facets[series][]": "RBRTE"}),
]
EIA_BASE = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

# --- Sina (DCE futures: PP, LLDPE) ----------------------------------------
# Mã -> (tên, nhóm, đơn vị, chỉ số trường giá trong chuỗi trả về).
# Lưu ý: layout trường của futures nội địa (nf_) có thể đổi -> kiểm tra lại nếu sai.
SINA_SYMBOLS = {
    "nf_PP0": ("PP kỳ hạn DCE", "hat_nhua_nen", "CNY/tấn", 8),
    "nf_L0":  ("LLDPE kỳ hạn DCE", "hat_nhua_nen", "CNY/tấn", 8),
}
SINA_URL = "https://hq.sinajs.cn/list="
SINA_REFERER = "https://finance.sina.com.cn"

# --- UN Comtrade (tùy chọn, mặc định TẮT vì là dữ liệu thương mại tháng) ---
COMTRADE_REQUESTS: list[dict] = []  # thêm khi cần; xem apis.fetch_comtrade
