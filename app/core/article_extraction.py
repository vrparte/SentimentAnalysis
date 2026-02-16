"""Article extraction utilities."""

import logging
from typing import Optional

import httpx
import trafilatura

from app.config import settings
from app.core.url_utils import canonicalize_url

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


def fetch_article(url: str, timeout: int = None, retries: int = None) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch article HTML.

    Returns (html_content, error_message).
    """
    timeout = timeout or settings.article_fetch_timeout
    retries = retries or settings.article_fetch_retries

    for attempt in range(retries):
        try:
            headers = {"User-Agent": USER_AGENT}
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return (response.text, None)
        except Exception as e:
            if attempt == retries - 1:
                error_msg = f"Failed to fetch {url} after {retries} attempts: {str(e)}"
                logger.error(error_msg)
                return (None, error_msg)
            logger.warning(f"Fetch attempt {attempt + 1} failed for {url}: {e}")

    return (None, "Max retries exceeded")


def extract_article_content(html: str, url: str) -> tuple[Optional[str], str]:
    """
    Extract main content from HTML.

    Returns (extracted_text, extraction_method).
    """
    if not html:
        return (None, "none")

    try:
        # Try trafilatura first (preferred)
        extracted = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
        if extracted:
            return (extracted, "trafilatura")
    except Exception as e:
        logger.warning(f"Trafilatura extraction failed for {url}: {e}")

    try:
        # Fallback to readability
        from readability import Document

        doc = Document(html)
        content = doc.summary()
        if content:
            # Remove HTML tags
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if text:
                return (text, "readability")
    except Exception as e:
        logger.warning(f"Readability extraction failed for {url}: {e}")

    # Last resort: extract from HTML
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=" ", strip=True)
        if text and len(text) > 100:  # Minimum content length
            return (text, "bs4")
    except Exception as e:
        logger.warning(f"BS4 extraction failed for {url}: {e}")

    return (None, "failed")


def fetch_and_extract(url: str) -> tuple[Optional[str], Optional[str], str]:
    """
    Fetch and extract article content.

    Returns (extracted_text, error_message, extraction_method).
    """
    html, error = fetch_article(url)
    if error:
        return (None, error, "none")

    canonical = canonicalize_url(url)
    extracted, method = extract_article_content(html, canonical)
    return (extracted, None, method)

