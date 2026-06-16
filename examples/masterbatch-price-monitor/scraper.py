"""Gọi Firecrawl để cào và bóc giá NVL thành JSON có cấu trúc.

Có 2 chiến lược:
  - batch_scrape_prices(): cào HÀNG LOẠT url + bật changeTracking (chỉ báo khi
    bảng giá thực sự đổi -> tiết kiệm credit, giảm nhiễu).
  - discover_urls_via_search(): tự tìm nguồn giá mới qua /search.
"""

import os
from firecrawl import FirecrawlApp

from schema import KetQuaTrang
from config import EXTRACT_PROMPT, SEARCH_LIMIT, CHANGE_TRACKING_TAG


def make_client() -> FirecrawlApp:
    api_url = os.getenv("FIRECRAWL_API_URL") or None
    api_key = os.getenv("FIRECRAWL_API_KEY") or None
    # Self-host: chỉ cần api_url. Cloud: chỉ cần api_key.
    if api_url:
        return FirecrawlApp(api_url=api_url, api_key=api_key or "self-hosted")
    return FirecrawlApp(api_key=api_key)


def _price_formats() -> list:
    """Formats dùng cho mỗi lần scrape: markdown (bắt buộc cho changeTracking),
    json (bóc giá theo schema) và changeTracking (so với lần cào trước)."""
    return [
        "markdown",
        {
            "type": "json",
            "prompt": EXTRACT_PROMPT,
            "schema": KetQuaTrang.model_json_schema(),
        },
        {
            "type": "changeTracking",
            "modes": ["json"],
            "tag": CHANGE_TRACKING_TAG,
        },
    ]


def batch_scrape_prices(app: FirecrawlApp, urls: list[str]) -> list[dict]:
    """Cào hàng loạt URL trong 1 job. Trả về danh sách theo từng trang:
        {url, change_status, san_pham: [...]}
    change_status thuộc: new | changed | same | removed (hoặc None nếu SDK cũ).
    """
    urls = [u for u in dict.fromkeys(urls) if u]  # bỏ trùng, bỏ rỗng
    if not urls:
        return []

    try:
        job = app.batch_scrape(urls, formats=_price_formats())
    except Exception as e:  # noqa: BLE001
        print(f"[batch_scrape][LỖI] {e}")
        return []

    docs = _job_documents(job)
    results: list[dict] = []
    for doc in docs:
        url = _doc_source_url(doc)
        data = _doc_json(doc)
        san_pham = data.get("san_pham", []) if isinstance(data, dict) else []
        results.append({
            "url": url,
            "change_status": _doc_change_status(doc),
            "san_pham": san_pham,
        })
        print(f"[batch] {url} -> {len(san_pham)} mục giá "
              f"(thay đổi: {_doc_change_status(doc) or 'n/a'})")
    return results


def discover_urls_via_search(app: FirecrawlApp, queries: list[str]) -> list[str]:
    """Tìm nguồn giá mới qua /search, trả về danh sách URL (chưa cào)."""
    found: list[str] = []
    for q in queries:
        try:
            res = app.search(q, limit=SEARCH_LIMIT)
            urls = [u for u in _search_urls(res) if u]
            print(f"[search] '{q}' -> {len(urls)} kết quả")
            found.extend(urls)
        except Exception as e:  # noqa: BLE001
            print(f"[search][LỖI] '{q}': {e}")
    return list(dict.fromkeys(found))


# --- helpers: chuẩn hóa response giữa các phiên bản SDK -------------------

def _job_documents(job) -> list:
    if hasattr(job, "data"):
        return job.data or []
    if isinstance(job, dict):
        return job.get("data", []) or []
    return []


def _doc_json(doc) -> dict:
    val = getattr(doc, "json", None)
    if val is None and isinstance(doc, dict):
        val = doc.get("json")
    return val or {}


def _doc_change_status(doc):
    ct = getattr(doc, "change_tracking", None)
    if ct is None and isinstance(doc, dict):
        ct = doc.get("changeTracking") or doc.get("change_tracking")
    if isinstance(ct, dict):
        return ct.get("changeStatus") or ct.get("change_status")
    return None


def _doc_source_url(doc) -> str:
    meta = getattr(doc, "metadata", None)
    if meta is None and isinstance(doc, dict):
        meta = doc.get("metadata")
    if hasattr(meta, "source_url"):
        return meta.source_url or getattr(meta, "url", "") or ""
    if isinstance(meta, dict):
        return meta.get("source_url") or meta.get("sourceURL") or meta.get("url") or ""
    return ""


def _search_urls(res) -> list[str]:
    web = getattr(res, "web", None)
    if web is None and isinstance(res, dict):
        web = res.get("web") or res.get("data")
    urls: list[str] = []
    for item in web or []:
        if isinstance(item, dict):
            urls.append(item.get("url"))
        else:
            urls.append(getattr(item, "url", None))
    return urls
