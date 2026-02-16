"""GDELT 2.1 Doc API provider."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from app.providers.base import SearchProvider, CandidateArticle, QuerySpec

logger = logging.getLogger(__name__)


class GDELTProvider(SearchProvider):
    """GDELT 2.1 Doc API provider."""

    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    def __init__(self):
        super().__init__("gdelt")

    def is_available(self) -> bool:
        """GDELT is always available (no API key required)."""
        return True

    def search(self, query_spec: QuerySpec) -> List[CandidateArticle]:
        """Search GDELT."""
        try:
            # GDELT query format
            query = query_spec.query

            # Build date filter if provided
            date_filter = ""
            if query_spec.date_from:
                date_from_str = query_spec.date_from.strftime("%Y%m%d%H%M%S")
                date_filter = f"&startdatetime={date_from_str}"
            if query_spec.date_to:
                date_to_str = query_spec.date_to.strftime("%Y%m%d%H%M%S")
                date_filter += f"&enddatetime={date_to_str}"

            # Default to last 24 hours if no date specified
            if not query_spec.date_from:
                date_from = datetime.utcnow() - timedelta(days=1)
                date_from_str = date_from.strftime("%Y%m%d%H%M%S")
                date_filter = f"&startdatetime={date_from_str}"

            url = f"{self.BASE_URL}?query={query}&mode=artlist&maxrecords={query_spec.max_results}{date_filter}&format=json"

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            articles = []
            if "articles" in data:
                for item in data["articles"][:query_spec.max_results]:
                    try:
                        published_at = None
                        if "seendate" in item:
                            try:
                                # GDELT date format: YYYYMMDDHHMMSS
                                date_str = str(item["seendate"])
                                if len(date_str) >= 8:
                                    published_at = datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
                            except Exception:
                                pass

                        article = CandidateArticle(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            source=item.get("domain", ""),
                            published_at=published_at,
                            snippet=item.get("snippet", ""),
                            provider_name=self.name,
                            language=query_spec.language,
                            country=query_spec.country,
                            state=query_spec.state,
                            district=query_spec.district,
                            city=query_spec.city,
                        )
                        articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing GDELT article: {e}")
                        continue

            return articles
        except Exception as e:
            logger.error(f"GDELT search error: {e}")
            return []

