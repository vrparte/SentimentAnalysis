"""Deduplication utilities."""

import hashlib
from typing import List, Dict, Optional

from simhash import Simhash

from app.models.article import Article, ExtractedContent


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of normalized content."""
    # Normalize: lowercase, strip whitespace
    normalized = " ".join(content.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_simhash(content: str, bits: int = 64) -> int:
    """Compute simhash for content similarity detection."""
    # Simple tokenization
    tokens = content.lower().split()
    return Simhash(tokens, f=bits).value


def are_similar_simhash(hash1: int, hash2: int, threshold: int = 3) -> bool:
    """Check if two simhashes are similar (Hamming distance <= threshold)."""
    return (hash1 ^ hash2).bit_count() <= threshold


def deduplicate_articles(
    articles: List[Dict],
    existing_articles: Optional[List[Article]] = None,
) -> List[Dict]:
    """
    Deduplicate articles based on:
    1. Exact URL match
    2. Canonical URL match
    3. Content hash similarity
    4. Title + source + date match
    """
    if existing_articles is None:
        existing_articles = []

    seen_urls = set()
    seen_canonical_urls = set()
    seen_content_hashes = set()
    seen_title_source_date = set()

    # Build lookup sets from existing articles
    for art in existing_articles:
        if art.url:
            seen_urls.add(art.url.lower().strip())
        if art.canonical_url:
            seen_canonical_urls.add(art.canonical_url.lower().strip())
        if art.extracted_content and art.extracted_content.content_hash:
            seen_content_hashes.add(art.extracted_content.content_hash)
        # Title + source + date
        if art.title and art.source and art.published_at:
            key = (
                art.title.lower().strip(),
                art.source.lower().strip(),
                art.published_at.date().isoformat(),
            )
            seen_title_source_date.add(key)

    deduplicated = []

    for article in articles:
        url = article.get("url", "").lower().strip()
        canonical_url = article.get("canonical_url", "").lower().strip()
        title = article.get("title", "").lower().strip()
        source = article.get("source", "").lower().strip()
        published_at = article.get("published_at")

        # Check exact URL
        if url and url in seen_urls:
            continue

        # Check canonical URL
        if canonical_url and canonical_url in seen_canonical_urls:
            continue

        # Check title + source + date
        if title and source and published_at:
            try:
                date_key = (
                    title,
                    source,
                    published_at.date().isoformat() if hasattr(published_at, "date") else str(published_at),
                )
                if date_key in seen_title_source_date:
                    continue
            except Exception:
                pass

        # Check content hash if available
        content = article.get("extracted_content", "")
        if content:
            content_hash = compute_content_hash(content)
            if content_hash in seen_content_hashes:
                continue
            article["content_hash"] = content_hash

        # Add to seen sets
        if url:
            seen_urls.add(url)
        if canonical_url:
            seen_canonical_urls.add(canonical_url)
        if content:
            seen_content_hashes.add(article.get("content_hash", ""))

        deduplicated.append(article)

    return deduplicated

