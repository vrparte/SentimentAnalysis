"""Search providers for article discovery."""

from app.providers.base import SearchProvider, CandidateArticle, QuerySpec
from app.providers.gdelt import GDELTProvider
from app.providers.bing import BingNewsProvider
from app.providers.serpapi import SerpAPIProvider
from app.providers.rss import RSSProvider

# Import India-specific providers conditionally to avoid errors if not available
try:
    from app.providers.newsdata import NewsDataProvider
    __all__ = [
        "SearchProvider",
        "CandidateArticle",
        "QuerySpec",
        "GDELTProvider",
        "BingNewsProvider",
        "SerpAPIProvider",
        "RSSProvider",
        "NewsDataProvider",
    ]
except ImportError:
    __all__ = [
        "SearchProvider",
        "CandidateArticle",
        "QuerySpec",
        "GDELTProvider",
        "BingNewsProvider",
        "SerpAPIProvider",
        "RSSProvider",
    ]

