"""NewsData.io provider - India-focused news API."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
import httpx

from app.providers.base import SearchProvider, CandidateArticle, QuerySpec
from app.config import settings

logger = logging.getLogger(__name__)


class NewsDataProvider(SearchProvider):
    """NewsData.io provider for Indian news."""

    BASE_URL = "https://newsdata.io/api/1/news"

    def __init__(self):
        super().__init__("newsdata")
        self.api_key = settings.newsdata_api_key

    def is_available(self) -> bool:
        """Check if NewsData.io API key is configured."""
        return bool(self.api_key)

    def search(self, query_spec: QuerySpec) -> List[CandidateArticle]:
        """Search NewsData.io for articles."""
        if not self.is_available():
            return []

        try:
            # NewsData.io parameters
            params = {
                "apikey": self.api_key,
                "q": query_spec.query,
                "language": query_spec.language,
                "country": query_spec.country.lower() if query_spec.country else "in",
                "size": min(query_spec.max_results, 10),  # Free tier limit
            }

            # Add date filters if provided
            if query_spec.date_from:
                # NewsData.io uses date in YYYY-MM-DD format
                params["from_date"] = query_spec.date_from.strftime("%Y-%m-%d")
            if query_spec.date_to:
                params["to_date"] = query_spec.date_to.strftime("%Y-%m-%d")

            # Add region/state filters if provided
            if query_spec.state:
                params["state"] = query_spec.state

            with httpx.Client(timeout=30.0) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            articles = []
            if "results" in data:
                for item in data["results"][:query_spec.max_results]:
                    try:
                        published_at = None
                        if item.get("pubDate"):
                            try:
                                # NewsData.io date format: "2024-01-15 12:00:00"
                                published_at = datetime.strptime(
                                    item["pubDate"], "%Y-%m-%d %H:%M:%S"
                                )
                            except Exception:
                                pass

                        # Extract source metadata
                        source = item.get("source_name", item.get("source_id", ""))
                        source_type, trust_score = self._classify_source(source)

                        article = CandidateArticle(
                            title=item.get("title", ""),
                            url=item.get("link", ""),
                            source=source,
                            published_at=published_at,
                            snippet=item.get("description", ""),
                            provider_name=self.name,
                            language=item.get("language", query_spec.language),
                            country=item.get("country", query_spec.country),
                            state=item.get("state", query_spec.state),
                            district=item.get("district", query_spec.district),
                            city=item.get("city", query_spec.city),
                            source_type=source_type,
                            source_trust_score=trust_score,
                        )
                        articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing NewsData.io article: {e}")
                        continue

            return articles
        except Exception as e:
            logger.error(f"NewsData.io search error: {e}")
            return []

    def _classify_source(self, source: str) -> tuple[str, int]:
        """Classify source and assign trust score."""
        from app.core.india_utils import classify_source_type
        return classify_source_type(source)

