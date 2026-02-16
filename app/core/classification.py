"""Classification: sentiment, severity, category."""

import logging
import re
from typing import List, Dict, Optional

from app.models.mention import Sentiment, Severity, Category

logger = logging.getLogger(__name__)


# Keyword dictionaries
NEGATIVE_HIGH_SEVERITY_KEYWORDS = [
    "arrested",
    "chargesheet",
    "raid",
    "fraud",
    "money laundering",
    "ED",
    "CBI",
    "conviction",
    "court order",
    "scam",
    "bankruptcy",
    "default",
    "sanction",
    "banned",
    "SEBI action",
    "enforcement directorate",
    "central bureau",
    "convicted",
    "sentenced",
    "jail",
    "prison",
]

NEGATIVE_MEDIUM_SEVERITY_KEYWORDS = [
    "investigation",
    "notice",
    "summons",
    "PIL",
    "lawsuit",
    "dispute",
    "allegation",
    "complaint",
    "inquiry",
    "probe",
    "scrutiny",
]

POSITIVE_KEYWORDS = [
    "appointed",
    "joins board",
    "award",
    "honoured",
    "recognized",
    "milestone",
    "expansion",
    "philanthropic",
    "achievement",
    "success",
    "excellence",
    "leadership",
    "commendation",
]

REGULATORY_KEYWORDS = [
    "SEBI",
    "RBI",
    "ED",
    "CBI",
    "regulatory",
    "compliance",
    "violation",
    "penalty",
    "fine",
    "action",
]

LEGAL_KEYWORDS = [
    "court",
    "judge",
    "judgment",
    "lawsuit",
    "litigation",
    "legal",
    "petition",
    "hearing",
    "verdict",
]

FINANCIAL_KEYWORDS = [
    "financial",
    "revenue",
    "profit",
    "loss",
    "earnings",
    "quarterly",
    "annual",
    "corporate",
    "business",
]

GOVERNANCE_KEYWORDS = [
    "board",
    "director",
    "governance",
    "appointment",
    "resignation",
    "independent director",
    "committee",
    "meeting",
]


def extractive_summary(text: str, max_sentences: int = 3) -> List[str]:
    """Extract first few sentences mentioning key terms."""
    if not text:
        return []

    # Simple sentence splitting
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # Return first few sentences
    return sentences[:max_sentences]


def classify_heuristic(
    title: str,
    snippet: str,
    content: Optional[str] = None,
    language: str = "en",
    country_profile: str = "IN",
) -> Dict:
    """
    Classify using heuristic rules with India-specific enhancements.

    Returns dict with:
    - sentiment: Sentiment enum
    - severity: Severity enum
    - category: Category enum
    - summary_bullets: List[str]
    - why_it_matters: str
    """
    from app.core.india_utils import (
        get_india_regulatory_context,
        get_india_legal_context,
        INDIA_HINDI_LEGAL_KEYWORDS,
    )
    from app.core.language_detection import is_indic_language
    
    full_text = f"{title} {snippet} {content or ''}".lower()
    
    # For Indic languages, add Hindi keywords to search (common transliterations appear)
    search_text = full_text
    if country_profile == "IN" and is_indic_language(language):
        # Note: For full Indic language support, translation would be needed
        # This is a basic enhancement - Hindi keywords may appear in transliterated form
        pass

    sentiment = Sentiment.NEUTRAL
    severity = Severity.LOW
    category = Category.OTHER

    # Get India-specific keywords if applicable
    regulatory_keywords = REGULATORY_KEYWORDS
    legal_keywords = LEGAL_KEYWORDS
    if country_profile == "IN":
        regulatory_keywords = get_india_regulatory_context() + REGULATORY_KEYWORDS
        legal_keywords = get_india_legal_context() + LEGAL_KEYWORDS

    # Check for negative high severity
    negative_high_count = sum(1 for kw in NEGATIVE_HIGH_SEVERITY_KEYWORDS if kw.lower() in search_text)
    if negative_high_count > 0:
        sentiment = Sentiment.NEGATIVE
        severity = Severity.HIGH
        if any(kw.lower() in search_text for kw in regulatory_keywords):
            category = Category.REGULATORY_ENFORCEMENT
        elif any(kw.lower() in search_text for kw in legal_keywords):
            # Check for specific litigation keywords
            litigation_keywords = ["nclt", "nclat", "civil suit", "criminal case", "fir", "charge sheet"]
            if any(kw.lower() in search_text for kw in litigation_keywords):
                category = Category.LITIGATION
            else:
                category = Category.LEGAL_COURT
        else:
            category = Category.PERSONAL_REPUTATION

    # Check for negative medium severity
    elif any(kw.lower() in search_text for kw in NEGATIVE_MEDIUM_SEVERITY_KEYWORDS):
        sentiment = Sentiment.NEGATIVE
        severity = Severity.MEDIUM
        if any(kw.lower() in search_text for kw in regulatory_keywords):
            category = Category.REGULATORY_ENFORCEMENT
        elif any(kw.lower() in search_text for kw in legal_keywords):
            litigation_keywords = ["nclt", "nclat", "civil suit", "criminal case", "fir", "charge sheet"]
            if any(kw.lower() in search_text for kw in litigation_keywords):
                category = Category.LITIGATION
            else:
                category = Category.LEGAL_COURT
        else:
            category = Category.PERSONAL_REPUTATION

    # Check for positive
    elif any(kw.lower() in search_text for kw in POSITIVE_KEYWORDS):
        sentiment = Sentiment.POSITIVE
        severity = Severity.LOW
        if any(kw in search_text for kw in ["award", "honoured", "recognized"]):
            category = Category.AWARDS_RECOGNITION
        elif any(kw in search_text for kw in GOVERNANCE_KEYWORDS):
            category = Category.GOVERNANCE_BOARD_APPOINTMENT
        else:
            category = Category.OTHER

    # Check category keywords (including India-specific)
    if category == Category.OTHER:
        if any(kw.lower() in search_text for kw in regulatory_keywords):
            category = Category.REGULATORY_ENFORCEMENT
        elif any(kw.lower() in search_text for kw in legal_keywords):
            litigation_keywords = ["nclt", "nclat", "civil suit", "criminal case"]
            if any(kw.lower() in search_text for kw in litigation_keywords):
                category = Category.LITIGATION
            else:
                category = Category.LEGAL_COURT
        elif any(kw in search_text for kw in FINANCIAL_KEYWORDS):
            category = Category.FINANCIAL_CORPORATE
        elif any(kw in search_text for kw in GOVERNANCE_KEYWORDS):
            # Check for governance disputes
            governance_dispute_keywords = ["board dispute", "related party", "governance issue", "conflict of interest"]
            if any(kw.lower() in search_text for kw in governance_dispute_keywords):
                category = Category.CORPORATE_GOVERNANCE
            else:
                category = Category.GOVERNANCE_BOARD_APPOINTMENT
        # Check for ESG/social/political
        elif any(kw in search_text for kw in ["controversy", "protest", "statement", "criticism", "allegation"]):
            category = Category.ESG_SOCIAL_POLITICAL

    # Generate summary
    summary_text = content or snippet or title
    summary_bullets = extractive_summary(summary_text, max_sentences=3)
    if not summary_bullets:
        summary_bullets = [title]

    # Why it matters (India-specific context)
    why_it_matters = ""
    if severity == Severity.HIGH:
        if category == Category.REGULATORY_ENFORCEMENT:
            why_it_matters = "High severity regulatory action requiring immediate board attention and compliance review."
        elif category in [Category.LEGAL_COURT, Category.LITIGATION]:
            why_it_matters = "High severity legal matter requiring immediate legal counsel and board notification."
        else:
            why_it_matters = "High severity item requiring immediate attention."
    elif severity == Severity.MEDIUM:
        why_it_matters = "Medium severity item that may require monitoring and periodic board updates."
    elif sentiment == Sentiment.POSITIVE:
        why_it_matters = "Positive news about the director - suitable for stakeholder communication."
    else:
        why_it_matters = "Neutral or low-severity mention."

    return {
        "sentiment": sentiment,
        "severity": severity,
        "category": category,
        "summary_bullets": summary_bullets[:6],  # Max 6 bullets
        "why_it_matters": why_it_matters,
    }


def classify_llm(
    title: str,
    snippet: str,
    content: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> Optional[Dict]:
    """
    Classify using LLM (OpenAI).

    Returns dict or None if LLM unavailable.
    """
    try:
        from openai import OpenAI

        if not api_key:
            return None

        client = OpenAI(api_key=api_key)

        # Truncate content if too long (keep more content for better context)
        # Increased from 2000 to 4000 characters for better context understanding
        content_preview = (content or "")[:4000] if content else ""

        prompt = f"""You are analyzing a news article about a corporate director or business leader for a board-level reputation monitoring system.

CRITICAL INSTRUCTIONS FOR ACCURATE SENTIMENT ANALYSIS:
1. CONTEXT MATTERS: Read the full article, not just keywords. Consider the complete meaning.
2. POSITIVE INDICATORS (mark as POSITIVE, LOW severity):
   - Appointments to committees, boards, prestigious roles
   - Awards, honors, recognition
   - Company achievements, profits, expansions
   - Positive statements, endorsements
   - Court cases dismissed, charges cleared, acquittals
   - Regulatory approvals, positive regulatory mentions
3. NEGATIVE INDICATORS (mark as NEGATIVE):
   - Actual wrongdoing: arrests, convictions, fraud, scams
   - Regulatory actions against: bans, penalties, enforcement actions
   - Legal issues with negative outcomes: lawsuits lost, guilty verdicts
   - Reputational damage: scandals, controversies
4. NEUTRAL INDICATORS (mark as NEUTRAL, LOW severity):
   - Routine business news: quarterly results, announcements
   - Regulatory compliance filings (not violations)
   - Court hearings without negative outcomes
   - General mentions in news articles
5. SEVERITY GUIDELINES:
   - HIGH: Serious negative events (arrests, convictions, major fraud, regulatory bans, criminal charges)
   - MEDIUM: Investigations, lawsuits pending, allegations, notices, inquiries (without conviction)
   - LOW: Routine news, neutral mentions, positive news, minor disputes

Article to analyze:
Title: {title}
Snippet: {snippet}
Content: {content_preview[:4000] if content_preview else "No additional content"}

Analyze the sentiment CAREFULLY by reading the full context. Do not rely on keywords alone. A mention of "SEBI" or "court" does not automatically mean negative - it could be positive (e.g., "appointed to SEBI committee") or neutral.

Return ONLY valid JSON, no other text:
{{
  "sentiment": "positive" | "negative" | "neutral",
  "severity": "low" | "medium" | "high",
  "category": "regulatory_enforcement" | "legal_court" | "litigation" | "financial_corporate" | "governance_board_appointment" | "awards_recognition" | "personal_reputation" | "corporate_governance" | "esg_social_political" | "other",
  "summary_bullets": ["key point 1", "key point 2", "key point 3"],
  "why_it_matters": "1-2 sentence explanation for board-level reputation monitoring"
}}"""

        # Use JSON mode if supported by the model (gpt-4o-mini and newer models)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,  # Lower temperature for more consistent classification
                max_tokens=800,  # Increased for better summaries
                response_format={"type": "json_object"},  # Force JSON output
            )
        except Exception as e:
            # Fallback for models that don't support response_format
            logger.warning(f"JSON mode not supported, using standard mode: {e}")
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )

        import json

        result_text = response.choices[0].message.content.strip()
        # Extract JSON if wrapped in markdown (some models still do this)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        # Parse JSON with better error handling
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {result_text[:200]}... Error: {e}")
            # Try to extract JSON object if it's embedded in text
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise

        # Validate and convert
        sentiment_map = {
            "positive": Sentiment.POSITIVE,
            "negative": Sentiment.NEGATIVE,
            "neutral": Sentiment.NEUTRAL,
            "mixed": Sentiment.MIXED,
        }
        severity_map = {
            "low": Severity.LOW,
            "medium": Severity.MEDIUM,
            "high": Severity.HIGH,
        }
        category_map = {
            "regulatory_enforcement": Category.REGULATORY_ENFORCEMENT,
            "legal_court": Category.LEGAL_COURT,
            "litigation": Category.LITIGATION,
            "financial_corporate": Category.FINANCIAL_CORPORATE,
            "governance_board_appointment": Category.GOVERNANCE_BOARD_APPOINTMENT,
            "awards_recognition": Category.AWARDS_RECOGNITION,
            "personal_reputation": Category.PERSONAL_REPUTATION,
            "corporate_governance": Category.CORPORATE_GOVERNANCE,
            "esg_social_political": Category.ESG_SOCIAL_POLITICAL,
            "other": Category.OTHER,
        }

        return {
            "sentiment": sentiment_map.get(result.get("sentiment", "neutral"), Sentiment.NEUTRAL),
            "severity": severity_map.get(result.get("severity", "low"), Severity.LOW),
            "category": category_map.get(result.get("category", "other"), Category.OTHER),
            "summary_bullets": result.get("summary_bullets", []),
            "why_it_matters": result.get("why_it_matters", ""),
        }
    except Exception as e:
        logger.error(f"LLM classification error: {e}")
        return None

