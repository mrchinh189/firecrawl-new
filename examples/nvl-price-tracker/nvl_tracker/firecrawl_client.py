"""Minimal client for the Firecrawl v2 /scrape endpoint (self-hosted or cloud)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

CLOUD_API_URL = "https://api.firecrawl.dev"


class ScrapeError(RuntimeError):
    pass


class FirecrawlClient:
    def __init__(
        self,
        api_url: str,
        api_key: str = "",
        fallback_api_key: str = "",
        timeout_ms: int = 60000,
        retries: int = 3,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.fallback_api_key = fallback_api_key
        self.timeout_ms = timeout_ms
        self.retries = retries

    def scrape(self, url: str, formats: list[Any], **options: Any) -> dict[str, Any]:
        """Scrape a URL on the configured instance.

        If every attempt fails and a cloud fallback key is configured, the
        same request is retried once against api.firecrawl.dev (which has
        fire-engine and handles anti-bot pages better than a self-hosted
        instance).
        """
        body: dict[str, Any] = {
            "url": url,
            "formats": formats,
            # Always fetch live prices, never a cached copy.
            "maxAge": 0,
            "timeout": self.timeout_ms,
            **options,
        }
        try:
            return self._post_with_retries(self.api_url, self.api_key, body)
        except ScrapeError as primary_error:
            if not self.fallback_api_key or self.api_url == CLOUD_API_URL:
                raise
            log.warning("Self-hosted scrape failed for %s (%s); trying cloud fallback", url, primary_error)
            return self._post_with_retries(CLOUD_API_URL, self.fallback_api_key, body, retries=1)

    def _post_with_retries(
        self, api_url: str, api_key: str, body: dict[str, Any], retries: int | None = None
    ) -> dict[str, Any]:
        attempts = retries or self.retries
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        last_error = "unknown error"
        for attempt in range(1, attempts + 1):
            try:
                resp = requests.post(
                    f"{api_url}/v2/scrape",
                    json=body,
                    headers=headers,
                    timeout=self.timeout_ms / 1000 + 30,
                )
                payload = resp.json() if resp.content else {}
                if resp.ok and payload.get("success"):
                    data = payload.get("data") or {}
                    status = (data.get("metadata") or {}).get("statusCode")
                    if status and int(status) >= 400:
                        last_error = f"target returned HTTP {status}"
                    else:
                        return data
                else:
                    last_error = f"HTTP {resp.status_code}: {payload.get('error') or resp.text[:300]}"
            except (requests.RequestException, ValueError) as exc:
                last_error = str(exc)

            if attempt < attempts:
                delay = 2**attempt
                log.info("Attempt %d/%d for %s failed (%s); retrying in %ds", attempt, attempts, body["url"], last_error, delay)
                time.sleep(delay)

        raise ScrapeError(last_error)
