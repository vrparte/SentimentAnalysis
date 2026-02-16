"""Language detection utilities for multilingual content."""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try to import language detection libraries
try:
    import langdetect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not available. Install with: pip install langdetect")

try:
    from langid import classify as langid_classify
    LANGID_AVAILABLE = True
except ImportError:
    LANGID_AVAILABLE = False
    logger.warning("langid not available. Install with: pip install langid")


def detect_language(text: str, method: str = "langid") -> Tuple[str, float]:
    """
    Detect language of text.
    
    Returns (language_code, confidence) tuple.
    Falls back to "en" if detection fails.
    """
    if not text or len(text.strip()) < 10:
        return ("en", 0.5)  # Default to English for short text
    
    text_sample = text[:1000]  # Sample first 1000 chars for speed
    
    try:
        if method == "langid" and LANGID_AVAILABLE:
            lang, confidence = langid_classify(text_sample)
            return (lang, confidence)
        elif method == "langdetect" and LANGDETECT_AVAILABLE:
            detected = langdetect.detect_langs(text_sample)
            if detected:
                best = detected[0]
                return (best.lang, best.prob)
        else:
            # Simple heuristic fallback
            # Check for Devanagari script (Hindi, Marathi, etc.)
            if any('\u0900' <= char <= '\u097F' for char in text_sample):
                return ("hi", 0.7)  # Likely Hindi or related
            # Check for Tamil script
            if any('\u0B80' <= char <= '\u0BFF' for char in text_sample):
                return ("ta", 0.7)
            # Check for Telugu script
            if any('\u0C00' <= char <= '\u0C7F' for char in text_sample):
                return ("te", 0.7)
            # Default to English
            return ("en", 0.6)
    except Exception as e:
        logger.warning(f"Language detection error: {e}")
        return ("en", 0.5)
    
    return ("en", 0.5)


def is_indic_language(language_code: str) -> bool:
    """Check if language code is an Indic language (excluding English)."""
    indic_languages = {"hi", "te", "ta", "mr", "gu", "kn", "ml", "or", "pa", "as", "bn"}
    return language_code in indic_languages


def should_translate(language_code: str, target_language: str = "en") -> bool:
    """Determine if text should be translated."""
    return is_indic_language(language_code) and target_language == "en"

