"""Mention/item endpoints."""

from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.api.auth import get_current_user
from app.database import get_db
from app.models.mention import Mention, Sentiment, Severity, Category

router = APIRouter()


@router.get("/")
def list_items(
    director_id: Optional[int] = None,
    sentiment: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    min_confidence: Optional[float] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
    include_unreviewed: bool = Query(False, description="Include items awaiting review"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List mentions/items with filters."""
    # By default, show confirmed items, but allow including unreviewed items
    if include_unreviewed:
        query = db.query(Mention)
    else:
        query = db.query(Mention).filter(Mention.is_confirmed == True)

    if director_id:
        query = query.filter(Mention.director_id == director_id)
    if sentiment:
        try:
            query = query.filter(Mention.sentiment == Sentiment(sentiment))
        except ValueError:
            pass
    if severity:
        try:
            query = query.filter(Mention.severity == Severity(severity))
        except ValueError:
            pass
    if category:
        try:
            query = query.filter(Mention.category == Category(category))
        except ValueError:
            pass
    if min_confidence is not None:
        query = query.filter(Mention.confidence >= min_confidence)
    if date_from:
        query = query.filter(Mention.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(Mention.created_at <= datetime.combine(date_to, datetime.max.time()))

    total = query.count()
    items = query.order_by(Mention.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": item.id,
                "director_id": item.director_id,
                "director_name": item.director.full_name,
                "article_id": item.article_id,
                "article_title": item.article.title,
                "article_url": item.article.url,
                "article_source": item.article.source,
                "article_published_at": item.article.published_at.isoformat() if item.article.published_at else None,
                "confidence": item.confidence,
                "sentiment": item.sentiment.value,
                "severity": item.severity.value,
                "category": item.category.value,
                "summary_bullets": item.summary_bullets,
                "why_it_matters": item.why_it_matters,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
    }


@router.get("/review-queue")
def get_review_queue(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get low-confidence items for review."""
    items = (
        db.query(Mention)
        .filter(Mention.is_reviewed == False, Mention.confidence < 0.5)
        .order_by(Mention.confidence.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": item.id,
            "director_id": item.director_id,
            "director_name": item.director.full_name,
            "article_title": item.article.title,
            "article_url": item.article.url,
            "confidence": item.confidence,
            "sentiment": item.sentiment.value,
            "severity": item.severity.value,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]


@router.post("/{item_id}/review")
def review_item(
    item_id: int,
    is_confirmed: bool,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Review and confirm/deny item."""
    item = db.query(Mention).filter(Mention.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.is_reviewed = True
    item.is_confirmed = is_confirmed
    db.commit()
    return {"message": "Item reviewed"}

