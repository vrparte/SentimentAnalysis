"""Tests for classification."""

from app.core.classification import classify_heuristic
from app.models.mention import Sentiment, Severity, Category


def test_classify_heuristic_negative_high():
    """Test negative high severity classification."""
    title = "Director arrested by ED in fraud case"
    snippet = "The director was arrested..."
    content = "The director was arrested by Enforcement Directorate in a fraud case."

    result = classify_heuristic(title, snippet, content)
    assert result["sentiment"] == Sentiment.NEGATIVE
    assert result["severity"] == Severity.HIGH
    assert result["category"] in [Category.REGULATORY_ENFORCEMENT, Category.LEGAL_COURT]


def test_classify_heuristic_positive():
    """Test positive classification."""
    title = "Director appointed to board, receives award"
    snippet = "The director was appointed..."
    content = "The director was appointed to the board and received an award."

    result = classify_heuristic(title, snippet, content)
    assert result["sentiment"] == Sentiment.POSITIVE
    assert result["severity"] == Severity.LOW

