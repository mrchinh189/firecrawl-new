"""
Cấu hình nguồn cào giá và danh mục nguyên vật liệu cho filler masterbatch.

Sửa file này để thêm/bớt nhà cung cấp và từ khóa tìm kiếm.
Không cần đụng tới code logic.
"""

# ---------------------------------------------------------------------------
# 1) Các URL bảng giá / trang sản phẩm muốn cào trực tiếp (dùng /extract).
#    - Web nhà cung cấp Việt Nam (bảng giá công khai) chạy tốt với self-host.
#    - Sàn lớn (Alibaba, Made-in-China) chống bot mạnh: nên dùng Firecrawl
#      cloud hoặc cấu hình PROXY_SERVER trong .env của Firecrawl.
# ---------------------------------------------------------------------------
PRICE_URLS = [
    # Ví dụ — thay bằng URL thật của bạn:
    # "https://nhuaviet-example.com/bang-gia-caco3",
    # "https://hatnhua-example.vn/lldpe",
    # "https://www.alibaba.com/showroom/calcium-carbonate-masterbatch.html",
]

# ---------------------------------------------------------------------------
# 2) Từ khóa để TỰ ĐỘNG tìm nguồn giá mới qua /search (web-wide).
#    Mỗi từ khóa sẽ được search và lấy nội dung các kết quả đầu để bóc giá.
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    "giá CaCO3 bột đá phủ stearic sản xuất filler masterbatch",
    "giá hạt nhựa LLDPE nguyên sinh",
    "giá hạt nhựa PP nguyên sinh",
    "giá axit stearic công nghiệp",
    "giá dầu trắng white oil nhựa",
    "calcium carbonate masterbatch price per ton",
    "LLDPE resin price",
    "PP homopolymer price",
]

# Số kết quả lấy mỗi truy vấn search
SEARCH_LIMIT = 5

# ---------------------------------------------------------------------------
# 3) Prompt mô tả dữ liệu cần bóc — tinh chỉnh để AI hiểu đúng ngành của bạn.
# ---------------------------------------------------------------------------
EXTRACT_PROMPT = (
    "Đây là trang liên quan tới nguyên vật liệu và phụ gia sản xuất filler "
    "masterbatch (hạt nhựa độn). Hãy lấy MỌI mức giá tìm được cho: bột đá / "
    "CaCO3 (có hoặc không phủ stearic), hạt nhựa nền (LLDPE, HDPE, PP, EVA), "
    "axit stearic, chất phủ bề mặt / coupling agent, dầu trắng (white oil), "
    "chất bôi trơn. Với mỗi mặt hàng lấy: tên, nhóm vật liệu, mức giá, đơn vị "
    "tính (VND/kg, USD/tấn...), nhà cung cấp và ngày báo giá nếu có. "
    "Bỏ qua các mục không có giá."
)
