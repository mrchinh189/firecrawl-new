import { Request } from "express";

/**
 * Resolve the hostname to use when building absolute URLs in API responses
 * (crawl/batch job URLs, pagination `next` links, etc.).
 *
 * Self-hosted instances commonly run behind a reverse proxy, so `req.get("host")`
 * returns the internal bind address (e.g. `localhost:3002`) instead of the public
 * hostname. Operators can set `SELF_HOSTED_DOMAIN` to the public host so the URLs
 * we hand back to clients are reachable (see #2964).
 *
 * Resolution order:
 *   1. `SELF_HOSTED_DOMAIN` env var, if set to a non-empty value
 *   2. the first `X-Forwarded-Host` value, if present
 *   3. `req.get("host")`
 *
 * The returned value is a host only (`host[:port]`), never a scheme or path, so
 * callers keep prefixing `${req.protocol}://`. `SELF_HOSTED_DOMAIN` is normalized
 * to a bare host even if the operator includes a scheme or path, which avoids
 * producing malformed URLs like `http://https://example.com/...`.
 */
export function getRequestHostname(req: Request): string | undefined {
  const configured = process.env.SELF_HOSTED_DOMAIN?.trim();
  if (configured) {
    const normalized = normalizeHost(configured);
    if (normalized) {
      return normalized;
    }
    // A misconfigured SELF_HOSTED_DOMAIN (e.g. contains spaces) must not leak
    // into the URL; fall through to the request-derived host instead.
  }

  const forwardedHost = req.get("x-forwarded-host");
  if (forwardedHost) {
    const first = forwardedHost.split(",")[0]?.trim();
    if (first) {
      return first;
    }
  }

  return req.get("host");
}

/**
 * Reduce a user-supplied domain to a bare `host[:port]`. Accepts values with or
 * without a scheme (`example.com`, `https://example.com`, `https://example.com/x`).
 * Returns undefined when the value cannot be parsed into a host, so callers do
 * not emit a malformed value.
 */
function normalizeHost(value: string): string | undefined {
  try {
    const withScheme = value.includes("://") ? value : `http://${value}`;
    return new URL(withScheme).host || undefined;
  } catch {
    return undefined;
  }
}
