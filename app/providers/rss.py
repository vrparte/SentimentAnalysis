"""RSS feed provider."""

import logging
from datetime import datetime
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from app.providers.base import SearchProvider, CandidateArticle, QuerySpec

logger = logging.getLogger(__name__)


class RSSProvider(SearchProvider):
    """RSS feed provider."""

    def __init__(self, feeds: Optional[List[str]] = None):
        super().__init__("rss")
        self.feeds = feeds or []

    def is_available(self) -> bool:
        """Check if feeds are configured."""
        return len(self.feeds) > 0

    def search(self, query_spec: QuerySpec) -> List[CandidateArticle]:
        """Search RSS feeds."""
        if not self.is_available():
            return []

        articles = []
        query_lower = query_spec.query.lower()

        for feed_url in self.feeds:
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(feed_url)
                    response.raise_for_status()
                    content = response.text

                soup = BeautifulSoup(content, "xml")
                items = soup.find_all("item")[:query_spec.max_results]

                for item in items:
                    try:
                        title = item.find("title")
                        title_text = title.text if title else ""

                        # Simple keyword matching
                        if query_lower not in title_text.lower():
                            continue

                        link = item.find("link")
                        url = link.text if link else ""

                        description = item.find("description")
                        snippet = description.text if description else ""

                        pub_date = item.find("pubDate")
                        published_at = None
                        if pub_date:
                            try:
                                from dateutil import parser

                                published_at = parser.parse(pub_date.text)
                            except Exception:
                                pass

                        source = item.find("source")
                        source_text = source.text if source else feed_url

                        # Classify source for trust scoring
                        from app.core.india_utils import classify_source_type
                        source_type, trust_score = classify_source_type(source_text, url)
                        
                        article = CandidateArticle(
                            title=title_text,
                            url=url,
                            source=source_text,
                            published_at=published_at,
                            snippet=snippet,
                            provider_name=self.name,
                            language=query_spec.language,
                            country=query_spec.country,
                            source_type=source_type,
                            source_trust_score=trust_score,
                        )
                        articles.append(article)
                    except Exception as e:
                        logger.warning(f"Error parsing RSS item: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Error fetching RSS feed {feed_url}: {e}")
                continue

        return articles

