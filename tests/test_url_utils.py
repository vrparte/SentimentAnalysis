"""Tests for URL utilities."""

from app.core.url_utils import canonicalize_url, normalize_url


def test_canonicalize_url():
    """Test URL canonicalization."""
    url1 = "https://example.com/article?id=1&name=test"
    url2 = "https://example.com/article?name=test&id=1"
    url3 = "https://example.com/article#fragment"

    canonical1 = canonicalize_url(url1)
    canonical2 = canonicalize_url(url2)
    canonical3 = canonicalize_url(url3)

    assert canonical1 == canonical2
    assert "#" not in canonical3

