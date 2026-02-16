"""Web UI routes."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.auth import get_current_user
from app.database import get_db
from app.models.director import Director
from app.models.report import Report
from app.models.mention import Mention, Sentiment, Severity
from app.models.article import Article

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Dashboard landing page."""
    # High severity count in last 24h
    high_severity_count_24h = db.query(Mention).filter(
        Mention.severity == Severity.HIGH,
        Mention.created_at >= datetime.utcnow() - timedelta(days=1)
    ).count()
    
    # Active directors
    active_directors = db.query(Director).filter(Director.is_active == True).count()
    
    # Mentions today
    mentions_today = db.query(Mention).filter(
        Mention.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
    ).count()
    
    # Pending reviews
    pending_reviews = db.query(Mention).filter(
        Mention.is_reviewed == False,
        Mention.confidence < 0.5
    ).count()
    
    # High severity total
    high_severity_count = db.query(Mention).filter(
        Mention.severity == Severity.HIGH
    ).count()
    
    # Today's highlights - top 5 by severity × confidence
    highlights = db.query(Mention).order_by(
        Mention.created_at.desc()
    ).limit(5).all()
    # Sort by severity score * confidence
    highlights = sorted(highlights, key=lambda m: (
        3 if m.severity == Severity.HIGH else (2 if m.severity == Severity.MEDIUM else 1)
    ) * m.confidence, reverse=True)[:5]
    
    # Recent activity (last 10 mentions)
    recent_mentions = db.query(Mention).order_by(Mention.created_at.desc()).limit(10).all()
    recent_activity = []
    for mention in recent_mentions:
        recent_activity.append({
            "time": mention.created_at.strftime('%Y-%m-%d %H:%M') if mention.created_at else 'Unknown',
            "type": "New Mention",
            "description": f"{mention.director.full_name} - {mention.article.title[:60]}"
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "high_severity_count_24h": high_severity_count_24h,
        "active_directors": active_directors,
        "mentions_today": mentions_today,
        "pending_reviews": pending_reviews,
        "high_severity_count": high_severity_count,
        "highlights": highlights,
        "recent_activity": recent_activity,
    })


@router.get("/mentions", response_class=HTMLResponse)
def mentions_page(
    request: Request,
    director_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    days: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Mentions page."""
    query = db.query(Mention)
    
    # Filters
    if director_id:
        query = query.filter(Mention.director_id == director_id)
    if severity:
        try:
            query = query.filter(Mention.severity == Severity(severity))
        except ValueError:
            pass
    if sentiment:
        try:
            query = query.filter(Mention.sentiment == Sentiment(sentiment))
        except ValueError:
            pass
    if days:
        query = query.filter(Mention.created_at >= datetime.utcnow() - timedelta(days=days))
    
    items = query.order_by(Mention.created_at.desc()).limit(200).all()
    directors = db.query(Director).filter(Director.is_active == True).all()
    
    return templates.TemplateResponse("mentions.html", {
        "request": request,
        "items": items,
        "directors": directors,
        "user": current_user,
        "director_id": director_id,
        "severity": severity,
        "sentiment": sentiment,
        "days": days,
    })


@router.get("/mentions/{mention_id}", response_class=HTMLResponse)
def mention_detail(
    request: Request,
    mention_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Mention detail page."""
    mention = db.query(Mention).filter(Mention.id == mention_id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Mention not found")
    
    return templates.TemplateResponse("mention_detail.html", {
        "request": request,
        "mention": mention,
        "user": current_user,
    })


@router.get("/directors", response_class=HTMLResponse)
def directors_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Directors list page."""
    directors = db.query(Director).all()
    return templates.TemplateResponse("directors.html", {
        "request": request,
        "directors": directors,
        "user": current_user,
    })


@router.get("/directors/{director_id}", response_class=HTMLResponse)
def director_profile(
    request: Request,
    director_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Director profile page."""
    director = db.query(Director).filter(Director.id == director_id).first()
    if not director:
        raise HTTPException(status_code=404, detail="Director not found")
    
    # Stats
    total_mentions = db.query(Mention).filter(Mention.director_id == director_id).count()
    
    # Sentiment distribution
    sentiment_counts = db.query(
        Mention.sentiment,
        func.count(Mention.id).label('count')
    ).filter(Mention.director_id == director_id).group_by(Mention.sentiment).all()
    
    # Recent mentions (last 7 days)
    recent_7d_mentions = db.query(Mention).filter(
        Mention.director_id == director_id,
        Mention.created_at >= datetime.utcnow() - timedelta(days=7)
    ).count()
    
    # Recent mentions list
    recent_mentions = db.query(Mention).filter(
        Mention.director_id == director_id
    ).order_by(Mention.created_at.desc()).limit(10).all()
    
    # Last mention date
    last_mention = db.query(Mention).filter(
        Mention.director_id == director_id
    ).order_by(Mention.created_at.desc()).first()
    
    return templates.TemplateResponse("director_profile.html", {
        "request": request,
        "director": director,
        "user": current_user,
        "total_mentions": total_mentions,
        "recent_7d_mentions": recent_7d_mentions,
        "sentiment_counts": sentiment_counts,
        "recent_mentions": recent_mentions,
        "last_mention": last_mention,
    })


@router.get("/reports", response_class=HTMLResponse)
def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Reports page."""
    reports = db.query(Report).order_by(Report.report_date.desc()).limit(50).all()
    directors = db.query(Director).filter(Director.is_active == True).all()
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "reports": reports,
        "directors": directors,
        "user": current_user,
    })


@router.get("/review-queue", response_class=HTMLResponse)
def review_queue_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Review queue page."""
    items = db.query(Mention).filter(
        Mention.is_reviewed == False,
        Mention.confidence < 0.5
    ).order_by(Mention.confidence.asc()).limit(50).all()
    return templates.TemplateResponse("review_queue.html", {
        "request": request,
        "items": items,
        "user": current_user,
    })


# Settings routes
@router.get("/settings/directors", response_class=HTMLResponse)
def settings_directors(
    request: Request,
    edit: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Settings - Directors management."""
    directors = db.query(Director).all()
    edit_director = None
    if edit:
        edit_director = db.query(Director).filter(Director.id == edit).first()
    
    return templates.TemplateResponse("settings_directors.html", {
        "request": request,
        "directors": directors,
        "edit_director": edit_director,
        "user": current_user,
    })


@router.get("/settings/scan", response_class=HTMLResponse)
def settings_scan(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Settings - Scan controls and history."""
    return templates.TemplateResponse("settings_scan.html", {
        "request": request,
        "user": current_user,
    })


@router.get("/settings/notifications", response_class=HTMLResponse)
def settings_notifications(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Settings - Notifications configuration."""
    from app.config import settings
    return templates.TemplateResponse("settings_notifications.html", {
        "request": request,
        "user": current_user,
        "app_settings": settings,
    })


@router.get("/settings/system", response_class=HTMLResponse)
def settings_system(
    request: Request,
    current_user = Depends(get_current_user),
):
    """Settings - System configuration."""
    from app.config import settings
    return templates.TemplateResponse("settings_system.html", {
        "request": request,
        "user": current_user,
        "app_settings": settings,
    })
