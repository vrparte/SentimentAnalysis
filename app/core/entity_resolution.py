"""Entity resolution and disambiguation."""

import re
from typing import List, Dict, Optional

from app.models.director import Director
from app.core.india_utils import (
    generate_indian_name_patterns,
    normalize_indian_name,
)


def find_name_in_text(text: str, names: List[str], case_sensitive: bool = False) -> bool:
    """Check if any of the names appear in text."""
    if not text:
        return False

    if not case_sensitive:
        text = text.lower()

    for name in names:
        if not name:
            continue
        search_name = name if case_sensitive else name.lower()
        # Word boundary matching for better precision
        pattern = r"\b" + re.escape(search_name) + r"\b"
        if re.search(pattern, text, re.IGNORECASE if not case_sensitive else 0):
            return True
    return False


def find_terms_in_text(text: str, terms: List[str], case_sensitive: bool = False) -> int:
    """Count how many context terms appear in text."""
    if not text or not terms:
        return 0

    if not case_sensitive:
        text = text.lower()

    count = 0
    for term in terms:
        if not term:
            continue
        search_term = term if case_sensitive else term.lower()
        pattern = r"\b" + re.escape(search_term) + r"\b"
        if re.search(pattern, text, re.IGNORECASE if not case_sensitive else 0):
            count += 1
    return count


def check_negative_terms(text: str, negative_terms: List[str]) -> bool:
    """Check if any negative terms appear (should exclude article)."""
    if not text or not negative_terms:
        return False

    text_lower = text.lower()
    for term in negative_terms:
        if not term:
            continue
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False


def compute_confidence(
    director: Director,
    title: str,
    snippet: str,
    extracted_content: Optional[str] = None,
    article_state: Optional[str] = None,
    article_city: Optional[str] = None,
) -> float:
    """
    Compute confidence score (0.0 to 1.0) that article is about this director.
    Enhanced with India-specific name patterns and location matching.

    Rules:
    - Name in title: +0.5
    - Name in snippet: +0.3
    - Name in content: +0.2
    - Context term match: +0.1 per term (max +0.3)
    - Location match (state/city): +0.1 (India-specific)
    - Negative term match: -1.0 (exclude)
    """
    # Generate Indian name patterns for better matching
    names = director.get_all_names()
    
    # Add generated Indian name patterns
    if hasattr(director, 'first_name') or hasattr(director, 'last_name'):
        indian_patterns = generate_indian_name_patterns(
            director.full_name,
            getattr(director, 'first_name', None),
            getattr(director, 'middle_names', None),
            getattr(director, 'last_name', None),
            director.aliases or []
        )
        names.extend(indian_patterns)
    
    # Normalize names for better matching
    names = [normalize_indian_name(name) for name in names]
    names = list(set(names))  # Remove duplicates
    
    context_terms = director.get_all_context_terms()
    negative_terms = director.get_all_negative_terms()

    # Check negative terms first
    full_text = f"{title} {snippet} {extracted_content or ''}"
    if check_negative_terms(full_text, negative_terms):
        return 0.0

    confidence = 0.0

    # Name in title (strong signal)
    if find_name_in_text(title, names):
        confidence += 0.5

    # Name in snippet
    if find_name_in_text(snippet, names):
        confidence += 0.3

    # Name in content
    if extracted_content and find_name_in_text(extracted_content, names):
        confidence += 0.2

    # Context terms
    context_matches = find_terms_in_text(full_text, context_terms)
    confidence += min(0.1 * context_matches, 0.3)

    # Location matching (India-specific): if article location matches company location
    if article_state and hasattr(director, 'hq_state') and director.hq_state:
        if article_state.lower() == director.hq_state.lower():
            confidence += 0.1
    if article_city and hasattr(director, 'hq_city') and director.hq_city:
        if article_city.lower() == director.hq_city.lower():
            confidence += 0.05

    # If name not found anywhere, very low confidence
    if confidence < 0.3:
        # Check if name appears at all
        if not find_name_in_text(full_text, names):
            return 0.0

    # Cap at 1.0
    return min(confidence, 1.0)


def resolve_director(
    directors: List[Director],
    title: str,
    snippet: str,
    extracted_content: Optional[str] = None,
    min_confidence: float = 0.3,
    article_state: Optional[str] = None,
    article_city: Optional[str] = None,
) -> Optional[tuple[Director, float]]:
    """
    Resolve which director (if any) an article is about.
    Enhanced with India-specific name matching and location context.

    Returns (Director, confidence) or None if no match above threshold.
    """
    best_match = None
    best_confidence = 0.0

    for director in directors:
        if not director.is_active:
            continue

        confidence = compute_confidence(
            director, title, snippet, extracted_content,
            article_state=article_state, article_city=article_city
        )
        if confidence > best_confidence and confidence >= min_confidence:
            best_confidence = confidence
            best_match = director

    if best_match:
        return (best_match, best_confidence)
    return None

