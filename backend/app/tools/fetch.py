"""Page fetch tool: httpx + BeautifulSoup text extraction.

15s timeout, max 100KB extracted text.
"""
from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

MAX_TEXT_BYTES = 100_000
TIMEOUT_SECONDS = 15.0


def fetch_page(url: str) -> str:
    """Fetch `url` and return extracted plain text, capped at 100KB."""
    try:
        with httpx.Client(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "CuratorBot/1.0"},
        ) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        return f"[fetch_error] Could not fetch {url}: {exc}"

    content_type = resp.headers.get("content-type", "")
    if "text/html" not in content_type and "application/xhtml" not in content_type:
        text = resp.text
    else:
        soup = BeautifulSoup(resp.text, "html.parser")

        # Respect a robots noindex meta tag if present.
        robots_meta = soup.find("meta", attrs={"name": "robots"})
        if robots_meta and "noindex" in (robots_meta.get("content", "").lower()):
            return f"[fetch_blocked] {url} sets robots meta noindex; skipping extraction."

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        text = encoded[:MAX_TEXT_BYTES].decode("utf-8", errors="ignore")
    return text
