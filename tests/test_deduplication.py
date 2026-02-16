"""Tests for deduplication."""

from app.core.deduplication import compute_content_hash, deduplicate_articles


def test_compute_content_hash():
    """Test content hash computation."""
    content1 = "This is a test article."
    content2 = "This is a test article."
    content3 = "This is a different article."

    hash1 = compute_content_hash(content1)
    hash2 = compute_content_hash(content2)
    hash3 = compute_content_hash(content3)

    assert hash1 == hash2
    assert hash1 != hash3


def test_deduplicate_articles():
    """Test article deduplication."""
    articles = [
        {"url": "https://example.com/article1", "title": "Article 1", "source": "Source 1"},
        {"url": "https://example.com/article1", "title": "Article 1", "source": "Source 1"},  # Duplicate URL
        {"url": "https://example.com/article2", "title": "Article 2", "source": "Source 2"},
    ]

    deduplicated = deduplicate_articles(articles)
    assert len(deduplicated) == 2

