"""SerpAPI provider for Google News."""

import logging
from datetime import datetime
from typing import List, Optional

import httpx

from app.config import settings
from app.providers.base import SearchProvider, CandidateArticle, QuerySpec

logger = logging.getLogger(__name__)


class SerpAPIProvider(SearchProvider):
    """SerpAPI provider for Google News."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        super().__init__("serpapi")
        self.api_key = settings.serpapi_key

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def search(self, query_spec: QuerySpec) -> List[CandidateArticle]:
        """Search Google News via SerpAPI."""
        if not self.is_available():
            logger.warning("SerpAPI key not configured")
            return []

        try:
            params = {
                "api_key": self.api_key,
                "engine": "google_news",
                "q": query_spec.query,
                "num": min(query_spec.max_results, 100),
            }

            # Add date filter if provided
            if query_spec.date_from:
                # SerpAPI uses tbs parameter for date filtering
                # tbs=cdr:1,cd_min:1/1/2024,cd_max:1/31/2024
                date_str = query_spec.date_from.strftime("%-m/%-d/%Y")
                params["tbs"] = f"cdr:1,cd_min:{date_str}"

            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            articles = []
            if "news_results" in data:
                for item in data["news_results"]:
                    try:
                        published_at = None
                        if "date" in item:
                            try:
                                # SerpAPI date format varies
                                date_str = item["date"]
                                # Try parsing common formats
                                for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d %b %Y"]:
                                    try:
                                        published_at = datetime.strptime(date_str, fmt)
                                        break
                                    except Exception:
                                        continue
                            except Exception:
                                pass

                        # Classify source for trust scoring
                        from app.core.india_utils import classify_source_type
                        source_name = item.get("source", "")
                        source_type, trust_score = classify_source_type(source_name, item.get("link", ""))
                        
                        article = CandidateArticle(
                            title=item.get("title", ""),
                            url=item.get("link", ""),
                            source=source_name,
                            published_at=published_at,
                            snippet=item.get("snippet", ""),
                            provider_name=self.name,
                            language=query_spec.language,
                            country=query_spec.country,
                            source_type=source_type,
                            source_trust_score=trust_score,
                        )
                        articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing SerpAPI article: {e}")
                        continue

            return articles
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return []

