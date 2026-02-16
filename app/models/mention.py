"""Mention model - links directors to articles."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, Integer, String, Text, Float, DateTime, ForeignKey, Index, Enum, JSON
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class Sentiment(str, enum.Enum):
    """Sentiment enum."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class Severity(str, enum.Enum):
    """Severity enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Category(str, enum.Enum):
    """Category enum."""

    REGULATORY_ENFORCEMENT = "regulatory_enforcement"
    LEGAL_COURT = "legal_court"
    LITIGATION = "litigation"  # Civil/criminal, NCLT/NCLAT
    FINANCIAL_CORPORATE = "financial_corporate"
    GOVERNANCE_BOARD_APPOINTMENT = "governance_board_appointment"
    CORPORATE_GOVERNANCE = "corporate_governance"  # Board disputes, related-party issues
    ESG_SOCIAL_POLITICAL = "esg_social_political"  # Controversial statements, protests
    AWARDS_RECOGNITION = "awards_recognition"
    PERSONAL_REPUTATION = "personal_reputation"
    OTHER = "other"


class Mention(Base):
    """Mention model - links director to article with classification."""

    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, index=True)
    director_id = Column(Integer, ForeignKey("directors.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    confidence = Column(Float, nullable=False, index=True)  # 0.0 to 1.0
    sentiment = Column(Enum(Sentiment), nullable=False, index=True)
    severity = Column(Enum(Severity), nullable=False, index=True)
    category = Column(Enum(Category), nullable=False, index=True)
    summary_bullets = Column(JSON, default=list)  # List of strings
    why_it_matters = Column(Text)
    is_reviewed = Column(Boolean, default=False)
    is_confirmed = Column(Boolean, default=True)  # False if marked as false positive
    alert_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    director = relationship("Director", back_populates="mentions")
    article = relationship("Article", back_populates="mentions")

    __table_args__ = (
        Index("idx_mention_confidence", "confidence"),
        Index("idx_mention_created_at", "created_at"),
        Index("idx_mention_sentiment_severity", "sentiment", "severity"),
    )

    def __repr__(self) -> str:
        return f"<Mention(id={self.id}, director_id={self.director_id}, confidence={self.confidence})>"

