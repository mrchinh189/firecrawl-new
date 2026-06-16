"""Schema dữ liệu giá mà Firecrawl /extract sẽ bóc ra."""

from typing import List, Optional
from pydantic import BaseModel, Field


class MatGia(BaseModel):
    ten_vat_lieu: str = Field(description="Tên mặt hàng, vd: CaCO3 phủ stearic, LLDPE, Axit stearic")
    nhom: str = Field(description="Nhóm: 'filler', 'hat_nhua_nen', hoặc 'phu_gia'")
    gia: float = Field(description="Mức giá dạng số")
    don_vi: str = Field(description="Đơn vị tính, vd: VND/kg, USD/tan")
    nha_cung_cap: Optional[str] = Field(default=None, description="Tên nhà cung cấp nếu có")
    ngay_bao_gia: Optional[str] = Field(default=None, description="Ngày báo giá nếu có, dạng YYYY-MM-DD")


class KetQuaTrang(BaseModel):
    san_pham: List[MatGia] = Field(default_factory=list)


class TyGia(BaseModel):
    ma_tien_te: str = Field(description="Mã tiền tệ, vd: USD, EUR, CNY")
    mua_tien_mat: Optional[float] = Field(default=None, description="Giá mua tiền mặt (VND)")
    mua_chuyen_khoan: Optional[float] = Field(default=None, description="Giá mua chuyển khoản (VND)")
    ban: Optional[float] = Field(default=None, description="Giá bán (VND)")


class KetQuaTyGia(BaseModel):
    ty_gia: List[TyGia] = Field(default_factory=list)
