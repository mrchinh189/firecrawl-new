"""Gọi Firecrawl để cào và bóc giá NVL thành JSON có cấu trúc."""

import os
from firecrawl import FirecrawlApp

from schema import KetQuaTrang
from config import EXTRACT_PROMPT, SEARCH_LIMIT


def make_client() -> FirecrawlApp:
    api_url = os.getenv("FIRECRAWL_API_URL") or None
    api_key = os.getenv("FIRECRAWL_API_KEY") or None
    # Self-host: chỉ cần api_url. Cloud: chỉ cần api_key.
    if api_url:
        return FirecrawlApp(api_url=api_url, api_key=api_key or "self-hosted")
    return FirecrawlApp(api_key=api_key)


def extract_prices_from_urls(app: FirecrawlApp, urls: list[str]) -> list[dict]:
    """Bóc giá từ danh sách URL bảng giá trực tiếp."""
    if not urls:
        return []
    rows: list[dict] = []
    for url in urls:
        try:
            res = app.extract(
                urls=[url],
                prompt=EXTRACT_PROMPT,
                schema=KetQuaTrang.model_json_schema(),
            )
            data = _unwrap(res)
            for item in data.get("san_pham", []):
                item["_nguon_url"] = url
                rows.append(item)
            print(f"[extract] {url} -> {len(data.get('san_pham', []))} mục giá")
        except Exception as e:  # noqa: BLE001
            print(f"[extract][LỖI] {url}: {e}")
    return rows


def discover_via_search(app: FirecrawlApp, queries: list[str]) -> list[dict]:
    """Tìm nguồn giá mới qua /search rồi bóc giá từ các kết quả."""
    rows: list[dict] = []
    for q in queries:
        try:
            search_res = app.search(q, limit=SEARCH_LIMIT)
            result_urls = [r.get("url") for r in _search_items(search_res) if r.get("url")]
            print(f"[search] '{q}' -> {len(result_urls)} kết quả")
            rows.extend(extract_prices_from_urls(app, result_urls))
        except Exception as e:  # noqa: BLE001
            print(f"[search][LỖI] '{q}': {e}")
    return rows


# --- helpers: chuẩn hóa response giữa các phiên bản SDK -------------------

def _unwrap(res) -> dict:
    """Lấy phần dữ liệu từ kết quả extract bất kể SDK trả object hay dict."""
    if hasattr(res, "data"):
        res = res.data
    if isinstance(res, dict):
        return res.get("data", res) if "data" in res else res
    return res or {}


def _search_items(res) -> list[dict]:
    if hasattr(res, "data"):
        res = res.data
    if isinstance(res, dict):
        return res.get("data", res.get("web", [])) or []
    if isinstance(res, list):
        return res
    return []
