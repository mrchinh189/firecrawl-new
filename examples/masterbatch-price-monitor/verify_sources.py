"""Kiểm tra nhanh khả năng truy cập các URL nguồn giá (chạy trên MÁY BẠN).

Báo HTTP status từng URL để biết: tồn tại (200), không có (404), chặn bot (403).
Lưu ý: 403 thường do chặn IP/bot -> cần Firecrawl cloud/stealth hoặc proxy,
không có nghĩa URL sai.

Chạy:  python verify_sources.py
"""

import requests

from config import WEB_PRICE_URLS, WEB_PRICE_URLS_ANTIBOT, FX_URLS, SINA_SYMBOLS, SINA_URL, SINA_REFERER

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def _ping(url: str, headers: dict | None = None) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": UA, **(headers or {})},
                         timeout=25, allow_redirects=True)
        return str(r.status_code)
    except Exception as e:  # noqa: BLE001
        return f"ERR ({type(e).__name__})"


def _note(code: str) -> str:
    if code == "200":
        return "OK"
    if code == "403":
        return "chặn bot -> cần cloud/proxy"
    if code == "404":
        return "KHÔNG tồn tại -> sửa URL/slug"
    return "kiểm tra lại"


def main() -> None:
    print("=== Nguồn web thường ===")
    for u in WEB_PRICE_URLS:
        c = _ping(u)
        print(f"  {c:<14} {_note(c):<28} {u}")

    print("\n=== Nguồn chống bot (kỳ vọng cần cloud/proxy) ===")
    for u in WEB_PRICE_URLS_ANTIBOT:
        c = _ping(u)
        print(f"  {c:<14} {_note(c):<28} {u}")

    print("\n=== Tỷ giá ===")
    for u in FX_URLS:
        c = _ping(u)
        print(f"  {c:<14} {_note(c):<28} {u}")

    print("\n=== Sina/DCE (cần Referer) ===")
    c = _ping(SINA_URL + ",".join(SINA_SYMBOLS.keys()), headers={"Referer": SINA_REFERER})
    print(f"  {c:<14} {_note(c):<28} {SINA_URL}{','.join(SINA_SYMBOLS.keys())}")


if __name__ == "__main__":
    main()
