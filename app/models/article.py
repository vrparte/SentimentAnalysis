"""Article models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Article(Base):
    """Article model - raw fetched article metadata."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), nullable=False, index=True)
    canonical_url = Column(String(2048), index=True)
    title = Column(String(512), nullable=False)
    source = Column(String(255))
    published_at = Column(DateTime, index=True)
    snippet = Column(Text)
    provider_name = Column(String(50))
    fetch_status = Column(String(50), default="pending")  # pending, success, failed
    fetch_error = Column(Text)
    # India-specific fields
    language = Column(String(10), default="en", index=True)  # ISO 639-1: en, hi, te, ta, etc.
    country = Column(String(2), default="IN", index=True)  # ISO 3166-1 alpha-2
    state = Column(String(100), index=True)  # State/Union Territory
    district = Column(String(100), index=True)  # District
    city = Column(String(100), index=True)  # City
    source_type = Column(String(50))  # mainstream_national, credible_regional, partisan, tabloid, unknown
    source_trust_score = Column(Integer, default=50)  # 0-100, higher = more credible
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    extracted_content = relationship("ExtractedContent", back_populates="article", uselist=False)
    mentions = relationship("Mention", back_populates="article", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_article_canonical_url", "canonical_url"),
        Index("idx_article_published_at", "published_at"),
        Index("idx_article_language_country", "language", "country"),
        Index("idx_article_state_district", "state", "district"),
    )

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title='{self.title[:50]}...')>"


class ExtractedContent(Base):
    """Extracted article content."""

    __tablename__ = "extracted_contents"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, unique=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), index=True)  # SHA256 hash
    language = Column(String(10), default="en")
    extraction_method = Column(String(50), default="trafilatura")
    created_at = Column(DateTime, default=datetime.utcnow)

    article = relationship("Article", back_populates="extracted_content")

    def __repr__(self) -> str:
        return f"<ExtractedContent(id={self.id}, article_id={self.article_id})>"

