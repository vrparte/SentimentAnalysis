"""URL canonicalization utilities."""

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def canonicalize_url(url: str) -> str:
    """
    Canonicalize URL by:
    - Removing fragments
    - Sorting query parameters
    - Normalizing scheme and netloc to lowercase
    - Removing default ports
    """
    try:
        parsed = urlparse(url)
        # Normalize scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if ":" in netloc:
            host, port = netloc.rsplit(":", 1)
            if (scheme == "http" and port == "80") or (scheme == "https" and port == "443"):
                netloc = host

        # Remove fragment
        fragment = ""

        # Sort query parameters
        query = ""
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_params = sorted(params.items())
            query = urlencode(sorted_params, doseq=True)

        canonical = urlunparse((scheme, netloc, parsed.path, parsed.params, query, fragment))
        return canonical.rstrip("/")
    except Exception:
        return url


def normalize_url(url: str) -> str:
    """Normalize URL for comparison."""
    return canonicalize_url(url).lower().strip()

