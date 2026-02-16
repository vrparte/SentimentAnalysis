"""Tests for entity resolution."""

from app.core.entity_resolution import compute_confidence, find_name_in_text
from app.models.director import Director


def test_find_name_in_text():
    """Test name finding in text."""
    text = "John Doe was appointed as independent director."
    names = ["John Doe", "J. Doe"]

    assert find_name_in_text(text, names) is True
    assert find_name_in_text("No match here", names) is False


def test_compute_confidence():
    """Test confidence computation."""
    director = Director(
        full_name="John Doe",
        aliases=["J. Doe"],
        context_terms=["ABC Corp", "independent director"],
        negative_terms=["actor"],
    )

    title = "John Doe appointed as independent director at ABC Corp"
    snippet = "John Doe has been appointed..."
    content = "John Doe, independent director at ABC Corp, was honored."

    confidence = compute_confidence(director, title, snippet, content)
    assert confidence > 0.5

    # Test with negative term
    title2 = "John Doe the actor wins award"
    confidence2 = compute_confidence(director, title2, "", "")
    assert confidence2 == 0.0

