"""Celery tasks for monitoring, extraction, classification, and reporting."""

import hashlib
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.director import Director
from app.models.article import Article, ExtractedContent
from app.models.mention import Mention, Sentiment, Severity, Category
from app.models.report import Report
from app.providers import (
    GDELTProvider,
    BingNewsProvider,
    SerpAPIProvider,
    RSSProvider,
    QuerySpec,
)
from app.core.url_utils import canonicalize_url
from app.core.deduplication import compute_content_hash, deduplicate_articles
from app.core.entity_resolution import resolve_director
from app.core.classification import classify_heuristic, classify_llm
from app.core.article_extraction import fetch_and_extract
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


@celery_app.task(bind=True, max_retries=3)
def daily_monitoring_job(self):
    """Main daily monitoring job."""
    logger.info("Starting daily monitoring job")
    db = get_db()
    try:
        directors = db.query(Director).filter(Director.is_active == True).all()
        if not directors:
            logger.warning("No active directors found")
            return

        # Initialize providers (including India-specific ones)
        providers = []
        enabled = settings.enabled_providers_list

        if "gdelt" in enabled:
            providers.append(GDELTProvider())
        if "bing" in enabled and BingNewsProvider().is_available():
            providers.append(BingNewsProvider())
        if "serpapi" in enabled and SerpAPIProvider().is_available():
            providers.append(SerpAPIProvider())
        if "newsdata" in enabled and NewsDataProvider().is_available():
            providers.append(NewsDataProvider())
        # RSS provider would need feed list from settings

        if not providers:
            logger.warning("No available providers")
            return

        # Process each director
        for director in directors:
            try:
                process_director.delay(director.id, [p.name for p in providers])
            except Exception as e:
                logger.error(f"Error queuing director {director.id}: {e}")

        logger.info(f"Queued {len(directors)} directors for processing")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def process_director(self, director_id: int, provider_names: List[str]):
    """Process a single director."""
    logger.info(f"Processing director {director_id}")
    db = get_db()
    try:
        director = db.query(Director).filter(Director.id == director_id).first()
        if not director or not director.is_active:
            logger.warning(f"Director {director_id} not found or inactive")
            return

        # Build queries with country profile
        queries = build_queries(director, country_profile=settings.country_profile)

        # Initialize providers (including India-specific ones)
        from app.providers.newsdata import NewsDataProvider
        providers = []
        if "gdelt" in provider_names and director.provider_gdelt_enabled:
            providers.append(GDELTProvider())
        if "bing" in provider_names and director.provider_bing_enabled:
            providers.append(BingNewsProvider())
        if "serpapi" in provider_names and director.provider_serpapi_enabled:
            providers.append(SerpAPIProvider())
        if "newsdata" in provider_names and director.provider_newsdata_enabled and NewsDataProvider().is_available():
            providers.append(NewsDataProvider())

        all_candidates = []

        # Search each provider with each query (with India-specific filters)
        for provider in providers:
            if not provider.is_available():
                continue
            for query in queries:
                try:
                    query_spec = QuerySpec(
                        query=query,
                        max_results=settings.max_articles_per_director_per_provider,
                        date_from=datetime.utcnow() - timedelta(days=1),
                        language="en",  # Default, can be enhanced to search multiple languages
                        country=settings.country_profile,
                        state=getattr(director, 'hq_state', None),
                        city=getattr(director, 'hq_city', None),
                    )
                    candidates = provider.search(query_spec)
                    all_candidates.extend(candidates)
                except Exception as e:
                    logger.error(f"Provider {provider.name} search error: {e}")

        # Deduplicate candidates
        existing_articles = db.query(Article).filter(
            Article.created_at >= datetime.utcnow() - timedelta(days=7)
        ).all()

        # Convert candidates to dict format for deduplication
        candidate_dicts = [
            {
                "url": c.url,
                "canonical_url": canonicalize_url(c.url),
                "title": c.title,
                "source": c.source,
                "published_at": c.published_at,
                "snippet": c.snippet,
                "provider_name": c.provider_name,
            }
            for c in all_candidates
        ]

        deduplicated = deduplicate_articles(candidate_dicts, existing_articles)

        logger.info(f"Found {len(deduplicated)} new articles for director {director_id}")

        # Process each article (limit to avoid queue overload)
        for article_dict in deduplicated[:20]:  # Limit to 20 per director per run
            try:
                process_article.delay(director_id, article_dict)
            except Exception as e:
                logger.error(f"Error queuing article for director {director_id}: {e}")

    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def process_article(self, director_id: int, article_dict: Dict):
    """Process a single article: fetch, extract, resolve, classify, store."""
    logger.info(f"Processing article: {article_dict.get('title', '')[:50]}")
    db = get_db()
    try:
        director = db.query(Director).filter(Director.id == director_id).first()
        if not director:
            return

        # Check if article already exists
        canonical_url = article_dict.get("canonical_url") or canonicalize_url(article_dict["url"])
        existing = db.query(Article).filter(Article.canonical_url == canonical_url).first()
        if existing:
            article = existing
        else:
            # Classify source type and trust score
            from app.core.india_utils import classify_source_type
            source_type, trust_score = classify_source_type(
                article_dict.get("source", ""),
                article_dict.get("url", "")
            )
            
            # Create article with India-specific metadata
            article = Article(
                url=article_dict["url"],
                canonical_url=canonical_url,
                title=article_dict["title"],
                source=article_dict.get("source"),
                published_at=article_dict.get("published_at"),
                snippet=article_dict.get("snippet"),
                provider_name=article_dict.get("provider_name"),
                fetch_status="pending",
                # India-specific fields
                language=article_dict.get("language", "en"),
                country=article_dict.get("country", settings.country_profile),
                state=article_dict.get("state"),
                district=article_dict.get("district"),
                city=article_dict.get("city"),
                source_type=source_type or article_dict.get("source_type"),
                source_trust_score=trust_score or article_dict.get("source_trust_score", 50),
            )
            db.add(article)
            db.flush()

        # Fetch and extract if not already done
        if not article.extracted_content:
            extracted_text, error, method = fetch_and_extract(article.url)
            if error:
                article.fetch_status = "failed"
                article.fetch_error = error
                db.commit()
                return

            if extracted_text:
                # Detect language if not already set
                from app.core.language_detection import detect_language
                if not article.language or article.language == "en":
                    detected_lang, lang_confidence = detect_language(
                        f"{article.title} {extracted_text[:500]}"
                    )
                    if lang_confidence > 0.6:
                        article.language = detected_lang
                
                content_hash = compute_content_hash(extracted_text)
                extracted = ExtractedContent(
                    article_id=article.id,
                    content=extracted_text,
                    content_hash=content_hash,
                    extraction_method=method,
                    language=article.language,  # Store detected language
                )
                db.add(extracted)
                article.fetch_status = "success"
            else:
                article.fetch_status = "failed"
                article.fetch_error = "No content extracted"
            db.commit()
            db.refresh(article)

        # Entity resolution with location context
        extracted_text = article.extracted_content.content if article.extracted_content else None
        resolution = resolve_director(
            [director],
            article.title,
            article.snippet or "",
            extracted_text,
            min_confidence=0.3,
            article_state=article.state,
            article_city=article.city,
        )

        if not resolution:
            logger.info(f"Article {article.id} did not match director {director_id}")
            return

        matched_director, confidence = resolution

        # Check if mention already exists
        existing_mention = db.query(Mention).filter(
            Mention.director_id == matched_director.id,
            Mention.article_id == article.id,
        ).first()
        if existing_mention:
            logger.info(f"Mention already exists for article {article.id}")
            return

        # Classification with language and country profile
        # Try LLM first if enabled, fallback to heuristic
        classification = None
        if settings.use_llm and settings.llm_api_key:
            try:
                logger.info(f"Attempting LLM classification for article {article.id}")
                classification = classify_llm(
                    article.title,
                    article.snippet or "",
                    extracted_text,
                    api_key=settings.llm_api_key,
                    model=settings.llm_model,
                )
                if classification:
                    logger.info(f"LLM classification successful for article {article.id}: sentiment={classification['sentiment']}, severity={classification['severity']}")
            except Exception as e:
                logger.error(f"LLM classification failed for article {article.id}: {e}", exc_info=True)
                classification = None
        
        # Fallback to heuristic if LLM not enabled or failed
        if not classification:
            logger.debug(f"Using heuristic classification for article {article.id}")
            classification = classify_heuristic(
                article.title,
                article.snippet or "",
                extracted_text,
                language=article.language or "en",
                country_profile=settings.country_profile,
            )

        # Create mention
        mention = Mention(
            director_id=matched_director.id,
            article_id=article.id,
            confidence=confidence,
            sentiment=classification["sentiment"],
            severity=classification["severity"],
            category=classification["category"],
            summary_bullets=classification["summary_bullets"],
            why_it_matters=classification["why_it_matters"],
            is_reviewed=False,
            is_confirmed=True,
        )
        db.add(mention)
        db.commit()

        # Check if alert should be sent
        if (
            mention.severity == Severity.HIGH
            and mention.confidence >= settings.confidence_threshold_alert
            and not mention.alert_sent
        ):
            send_alert.delay(mention.id)

        logger.info(f"Created mention {mention.id} for director {matched_director.id}")

    except Exception as e:
        logger.error(f"Error processing article: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task
def send_alert(mention_id: int):
    """Send immediate alert email for high-severity mention."""
    from app.core.email import send_alert_email

    db = get_db()
    try:
        mention = db.query(Mention).filter(Mention.id == mention_id).first()
        if not mention or mention.alert_sent:
            return

        send_alert_email(mention)
        mention.alert_sent = True
        db.commit()
    finally:
        db.close()


@celery_app.task
def generate_daily_report(report_date_str: Optional[str] = None):
    """Generate daily digest report."""
    from app.core.reporting import generate_report

    if report_date_str:
        report_date = date.fromisoformat(report_date_str)
    else:
        report_date = date.today()

    logger.info(f"Generating daily report for {report_date}")
    return generate_report(report_date)


@celery_app.task
def cleanup_old_data():
    """Clean up old data based on retention policy."""
    db = get_db()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=settings.data_retention_days)

        # Delete old mentions (cascade will handle articles if no other mentions)
        deleted_mentions = db.query(Mention).filter(Mention.created_at < cutoff_date).delete()
        logger.info(f"Deleted {deleted_mentions} old mentions")

        # Delete orphaned articles
        deleted_articles = db.query(Article).filter(
            Article.created_at < cutoff_date,
            ~Article.mentions.any(),
        ).delete()
        logger.info(f"Deleted {deleted_articles} orphaned articles")

        db.commit()
    except Exception as e:
        logger.error(f"Error in cleanup: {e}")
        db.rollback()
    finally:
        db.close()


def build_queries(director: Director, country_profile: str = "IN") -> List[str]:
    """Build search queries for a director with India-specific enhancements."""
    from app.core.india_utils import (
        get_india_regulatory_context,
        get_india_legal_context,
        generate_indian_name_patterns,
    )
    
    name = director.full_name
    context_terms = director.get_all_context_terms()
    negative_terms = director.get_all_negative_terms()

    queries = []

    # Generate Indian name patterns for better recall
    name_patterns = [name]
    if hasattr(director, 'first_name') or hasattr(director, 'last_name'):
        indian_patterns = generate_indian_name_patterns(
            director.full_name,
            getattr(director, 'first_name', None),
            getattr(director, 'middle_names', None),
            getattr(director, 'last_name', None),
            director.aliases or []
        )
        name_patterns.extend(indian_patterns[:3])  # Use top 3 patterns

    # Recall query: just the name (use most common pattern)
    queries.append(f'"{name_patterns[0]}"')

    # Precision queries with context terms
    if context_terms:
        context_str = " OR ".join([f'"{term}"' for term in context_terms[:3]])
        queries.append(f'"{name}" AND ({context_str})')

    # India-specific regulatory/legal query
    if country_profile == "IN":
        regulatory_terms = get_india_regulatory_context()
        legal_terms = get_india_legal_context()
        # Use director's India context profile if available
        if hasattr(director, 'india_context_profile') and director.india_context_profile:
            regulatory_terms = director.india_context_profile.get("regulatory_terms", regulatory_terms)
            legal_terms = director.india_context_profile.get("legal_terms", legal_terms)
        
        regulatory_str = " OR ".join([f'"{term}"' for term in regulatory_terms[:8]])
        legal_str = " OR ".join([f'"{term}"' for term in legal_terms[:6]])
        queries.append(f'"{name}" AND ({regulatory_str})')
        queries.append(f'"{name}" AND ({legal_str})')
    else:
        # Generic regulatory/legal query
        queries.append(f'"{name}" AND ("SEBI" OR "RBI" OR "ED" OR "CBI" OR "court" OR "fraud" OR "investigation")')

    # Positive query
    queries.append(f'"{name}" AND ("award" OR "appointed" OR "joins" OR "honoured")')

    return queries[:6]  # Limit to 6 queries (increased for better coverage)

