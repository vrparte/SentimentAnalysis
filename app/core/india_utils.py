"""India-specific utilities for name matching, query building, and context."""

import re
from typing import List, Dict, Set


# India-specific regulatory and legal keywords
INDIA_REGULATORY_KEYWORDS = [
    "SEBI", "RBI", "ED", "CBI", "SFIO", "NCLT", "NCLAT", "MCA",
    "IT department", "Income Tax", "GST", "DRI", "SFIO investigation",
    "Ministry of Corporate Affairs", "MCA order", "SEBI order",
    "RBI action", "Enforcement Directorate", "Central Bureau of Investigation",
    "Serious Fraud Investigation Office", "National Company Law Tribunal",
    "National Company Law Appellate Tribunal", "Income Tax Department",
]

INDIA_LEGAL_KEYWORDS = [
    "Supreme Court", "High Court", "District Court", "Session Court",
    "FIR registered", "charge sheet", "show-cause notice", "attachment of assets",
    "arrest warrant", "bail", "prosecution", "litigation", "PIL", "writ petition",
    "contempt of court", "stay order", "interim order", "final order",
]

# Hindi keywords for legal/regulatory context (common transliterations)
INDIA_HINDI_LEGAL_KEYWORDS = [
    "गिरफ्तार",  # arrested
    "जांच",      # investigation
    "धोखाधड़ी",  # fraud
    "अपराध",     # crime
    "नोटिस",     # notice
    "अदालत",     # court
]

# Common Indian honorifics
INDIAN_HONORIFICS = [
    "Shri", "Shrimati", "Smt", "Dr", "Dr.", "Prof", "Prof.", "Mr", "Mr.", "Mrs", "Mrs.",
    "Ms", "Ms.", "Sir", "Madam", "Justice", "Hon'ble", "Honorable",
]

# State abbreviations and full names
INDIAN_STATES = {
    "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh", "AS": "Assam",
    "BR": "Bihar", "CT": "Chhattisgarh", "GA": "Goa", "GJ": "Gujarat",
    "HR": "Haryana", "HP": "Himachal Pradesh", "JK": "Jammu and Kashmir",
    "JH": "Jharkhand", "KA": "Karnataka", "KL": "Kerala", "MP": "Madhya Pradesh",
    "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya", "MZ": "Mizoram",
    "NL": "Nagaland", "OR": "Odisha", "PB": "Punjab", "RJ": "Rajasthan",
    "SK": "Sikkim", "TN": "Tamil Nadu", "TG": "Telangana", "TR": "Tripura",
    "UP": "Uttar Pradesh", "UK": "Uttarakhand", "WB": "West Bengal",
    # Union Territories
    "AN": "Andaman and Nicobar Islands", "CH": "Chandigarh",
    "DN": "Dadra and Nagar Haveli and Daman and Diu", "DL": "Delhi",
    "LD": "Ladakh", "LA": "Lakshadweep", "PY": "Puducherry",
}

# Supported Indian languages (ISO 639-1)
INDIA_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "or": "Odia",
    "pa": "Punjabi",
    "as": "Assamese",
    "bn": "Bengali",
}


def generate_indian_name_patterns(full_name: str, first_name: str = None, 
                                  middle_names: str = None, last_name: str = None,
                                  aliases: List[str] = None) -> List[str]:
    """
    Generate name patterns for Indian name matching.
    
    Handles:
    - Honorifics (Shri, Dr., etc.)
    - Multiple spellings
    - Initials (R. Kumar, Ramesh A. Kumar)
    - Name variations
    """
    patterns = []
    aliases = aliases or []
    
    # Base name variations
    name_variants = [full_name]
    if aliases:
        name_variants.extend(aliases)
    
    # Add structured name combinations
    if first_name and last_name:
        name_variants.append(f"{first_name} {last_name}")
        if middle_names:
            # With middle name
            name_variants.append(f"{first_name} {middle_names} {last_name}")
            # With middle initial
            middle_init = ".".join([m[0] for m in middle_names.split() if m]) + "."
            name_variants.append(f"{first_name} {middle_init} {last_name}")
        # First name + initial + last name
        name_variants.append(f"{first_name[0]}. {last_name}")
    
    # Generate patterns with and without honorifics
    for name in name_variants:
        # Original
        patterns.append(name)
        # Remove common honorifics
        name_clean = name
        for honorific in INDIAN_HONORIFICS:
            if name_clean.startswith(honorific + " "):
                name_clean = name_clean[len(honorific) + 1:].strip()
                patterns.append(name_clean)
        # Add honorifics if not present
        if not any(name.startswith(h) for h in INDIAN_HONORIFICS):
            for honorific in ["Shri", "Dr.", "Mr."]:
                patterns.append(f"{honorific} {name}")
    
    return list(set(patterns))  # Remove duplicates


def get_india_regulatory_context() -> List[str]:
    """Get default India regulatory keywords."""
    return INDIA_REGULATORY_KEYWORDS.copy()


def get_india_legal_context() -> List[str]:
    """Get default India legal keywords."""
    return INDIA_LEGAL_KEYWORDS.copy()


def get_india_context_profile() -> Dict[str, List[str]]:
    """Get default India context profile for directors."""
    return {
        "regulatory_terms": INDIA_REGULATORY_KEYWORDS.copy(),
        "legal_terms": INDIA_LEGAL_KEYWORDS.copy(),
        "hindi_legal_terms": INDIA_HINDI_LEGAL_KEYWORDS.copy(),
    }


def normalize_indian_name(name: str) -> str:
    """Normalize Indian name for matching (remove honorifics, extra spaces)."""
    name = name.strip()
    # Remove honorifics
    for honorific in INDIAN_HONORIFICS:
        if name.lower().startswith(honorific.lower() + " "):
            name = name[len(honorific):].strip()
    # Normalize spaces
    name = re.sub(r'\s+', ' ', name)
    return name


def is_indian_language(language_code: str) -> bool:
    """Check if language code is an Indian language."""
    return language_code in INDIA_LANGUAGES


def get_language_name(language_code: str) -> str:
    """Get full language name from ISO 639-1 code."""
    return INDIA_LANGUAGES.get(language_code, language_code)


def get_state_name(state_code: str) -> str:
    """Get full state name from abbreviation."""
    return INDIAN_STATES.get(state_code.upper(), state_code)


def classify_source_type(source: str, domain: str = None) -> tuple[str, int]:
    """
    Classify source type and assign trust score.
    
    Returns (source_type, trust_score):
    - mainstream_national: 80-100 (e.g., The Hindu, Times of India, Hindustan Times)
    - credible_regional: 60-79 (e.g., regional English dailies)
    - vernacular_regional: 50-69 (regional language media)
    - partisan: 30-49 (opinion-heavy, biased outlets)
    - tabloid: 20-39 (sensationalist)
    - unknown: 40 (default)
    """
    if not source:
        return ("unknown", 40)
    
    source_lower = source.lower()
    domain_lower = (domain or "").lower()
    
    # Mainstream national (high trust)
    mainstream_national = [
        "times of india", "the hindu", "hindustan times", "indian express",
        "economic times", "mint", "business standard", "livemint",
        "ndtv", "cnn-news18", "news18", "reuters india", "pti",
    ]
    
    # Credible regional
    credible_regional = [
        "deccan herald", "the telegraph", "the tribune", "daily pioneer",
        "deccan chronicle", "asian age",
    ]
    
    # Partisan/sensationalist indicators
    partisan_keywords = [
        "opindia", "republic", "aaj tak", "zee news", "scoopwhoop",
    ]
    
    # Tabloid indicators
    tabloid_keywords = [
        "mid-day", "mumbai mirror", "daily bhaskar",
    ]
    
    # Check mainstream national
    if any(name in source_lower or name in domain_lower for name in mainstream_national):
        return ("mainstream_national", 85)
    
    # Check credible regional
    if any(name in source_lower or name in domain_lower for name in credible_regional):
        return ("credible_regional", 70)
    
    # Check partisan
    if any(keyword in source_lower or keyword in domain_lower for keyword in partisan_keywords):
        return ("partisan", 35)
    
    # Check tabloid
    if any(keyword in source_lower or keyword in domain_lower for keyword in tabloid_keywords):
        return ("tabloid", 25)
    
    # Default
    return ("unknown", 40)

