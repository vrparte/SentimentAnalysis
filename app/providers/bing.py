"""Bing News Search API provider."""

import logging
from datetime import datetime
from typing import List, Optional

import httpx

from app.config import settings
from app.providers.base import SearchProvider, CandidateArticle, QuerySpec

logger = logging.getLogger(__name__)


class BingNewsProvider(SearchProvider):
    """Bing News Search API provider."""

    BASE_URL = "https://api.bing.microsoft.com/v7.0/news/search"

    def __init__(self):
        super().__init__("bing")
        self.api_key = settings.bing_news_key

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def search(self, query_spec: QuerySpec) -> List[CandidateArticle]:
        """Search Bing News."""
        if not self.is_available():
            logger.warning("Bing News API key not configured")
            return []

        try:
            headers = {"Ocp-Apim-Subscription-Key": self.api_key}
            params = {
                "q": query_spec.query,
                "count": min(query_spec.max_results, 100),  # Bing max is 100
                "mkt": "en-IN",  # India market
                "sortBy": "Date",
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.BASE_URL, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

            articles = []
            if "value" in data:
                for item in data["value"]:
                    try:
                        published_at = None
                        if "datePublished" in item:
                            try:
                                # Bing format: ISO 8601
                                published_at = datetime.fromisoformat(
                                    item["datePublished"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        # Classify source for trust scoring
                        from app.core.india_utils import classify_source_type
                        source_name = item.get("provider", [{}])[0].get("name", "") if item.get("provider") else ""
                        source_type, trust_score = classify_source_type(source_name, item.get("url", ""))
                        
                        article = CandidateArticle(
                            title=item.get("name", ""),
                            url=item.get("url", ""),
                            source=source_name,
                            published_at=published_at,
                            snippet=item.get("description", ""),
                            provider_name=self.name,
                            language=query_spec.language,
                            country=query_spec.country,
                            source_type=source_type,
                            source_trust_score=trust_score,
                        )
                        articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing Bing article: {e}")
                        continue

            return articles
        except Exception as e:
            logger.error(f"Bing News search error: {e}")
            return []

