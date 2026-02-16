"""Base provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class CandidateArticle:
    """Candidate article from a search provider."""

    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    snippet: str
    provider_name: str
    # India-specific metadata
    language: str = "en"  # ISO 639-1
    country: str = "IN"  # ISO 3166-1 alpha-2
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    source_type: Optional[str] = None  # mainstream_national, credible_regional, etc.
    source_trust_score: int = 50  # 0-100


@dataclass
class QuerySpec:
    """Search query specification."""

    query: str
    max_results: int = 50
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    language: str = "en"  # ISO 639-1: en, hi, te, ta, mr, gu, kn, ml, or, pa, as, bn
    # India-specific filters
    country: str = "IN"
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None  # North, South, East, West, Central, Northeast


class SearchProvider(ABC):
    """Base class for search providers."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(self, query_spec: QuerySpec) -> List[CandidateArticle]:
        """
        Search for articles.

        Returns list of CandidateArticle objects.
        Should handle errors gracefully and return empty list on failure.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (API key configured, etc.)."""
        pass

