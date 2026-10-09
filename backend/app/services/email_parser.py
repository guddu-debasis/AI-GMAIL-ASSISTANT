import re
import html
import base64
from typing import Optional, Dict, Any, List


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML string to prevent XSS while preserving basic readable line structure.
    Strips script, style, iframe, object tags and unsafe attributes.
    """
    if not html_content:
        return ""
    # Strip script/style/iframe tags and their contents
    clean = re.sub(r"<(script|style|iframe|object|embed)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    # Replace <br> and <p> with newlines for text readability
    clean = re.sub(r"<br\s*/?>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</p>", "\n\n", clean, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    clean = re.sub(r"<[^>]+>", "", clean)
    # Unescape HTML entities
    clean = html.unescape(clean)
    return clean.strip()


def extract_plain_text_from_mime(payload: Dict[str, Any]) -> str:
    """
    Extracts plain text or sanitized HTML body from Gmail API message payload.
    Handles multipart/alternative, multipart/mixed, and text/plain.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    # If top-level body contains data
    if body_data and mime_type in ["text/plain", "text/html"]:
        decoded = base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
        if mime_type == "text/html":
            return sanitize_html(decoded)
        return decoded.strip()

    parts = payload.get("parts", [])
    plain_text = ""
    html_text = ""

    for part in parts:
        part_mime = part.get("mimeType", "")
        part_data = part.get("body", {}).get("data")
        if part_data:
            decoded = base64.urlsafe_b64decode(part_data + "==").decode("utf-8", errors="replace")
            if part_mime == "text/plain":
                plain_text = decoded.strip()
                break
            elif part_mime == "text/html":
                html_text = sanitize_html(decoded)
        # Recurse if nested parts
        if "parts" in part:
            nested = extract_plain_text_from_mime(part)
            if nested:
                return nested

    return plain_text or html_text or ""


def parse_email_headers(headers: List[Dict[str, str]]) -> Dict[str, str]:
    """Extract standard headers into a clean lowercase-key dictionary."""
    extracted = {}
    for h in headers:
        name = h.get("name", "").lower()
        extracted[name] = h.get("value", "")
    return extracted
