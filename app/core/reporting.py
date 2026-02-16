"""Report generation utilities."""

import logging
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from jinja2 import Template
from weasyprint import HTML

from app.config import settings
from app.database import SessionLocal
from app.models.director import Director
from app.models.mention import Mention, Sentiment, Severity
from app.models.report import Report
from app.core.email import send_daily_digest

logger = logging.getLogger(__name__)


REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Director Media Monitoring Report - {{ report_date }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
        .summary { background: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px; }
        .director-section { margin: 30px 0; }
        .mention-item { margin: 15px 0; padding: 10px; border-left: 3px solid #ddd; }
        .mention-item.high { border-left-color: #d32f2f; }
        .mention-item.medium { border-left-color: #f57c00; }
        .mention-item.low { border-left-color: #388e3c; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 0.85em; }
        .badge.positive { background: #4caf50; color: white; }
        .badge.negative { background: #f44336; color: white; }
        .badge.neutral { background: #9e9e9e; color: white; }
        .badge.mixed { background: #ff9800; color: white; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-box { flex: 1; padding: 15px; background: white; border: 1px solid #ddd; border-radius: 5px; }
        .stat-number { font-size: 2em; font-weight: bold; }
        .stat-label { color: #666; }
    </style>
</head>
<body>
    <h1>Director Media Monitoring Report</h1>
    <p><strong>Company:</strong> {{ company_name }}</p>
    <p><strong>Report Date:</strong> {{ report_date }}</p>
    <p><strong>Generated:</strong> {{ generated_at }}</p>

    <div class="summary">
        <h2>Executive Summary</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{{ stats.total_mentions }}</div>
                <div class="stat-label">Total Mentions</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.high_severity }}</div>
                <div class="stat-label">High Severity</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.positive }}</div>
                <div class="stat-label">Positive</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{{ stats.negative }}</div>
                <div class="stat-label">Negative</div>
            </div>
        </div>
    </div>

    <h2>Director Reports</h2>
    {% for director_data in directors_data %}
    <div class="director-section">
        <h3>{{ director_data.director.full_name }}</h3>
        <p><strong>New items (24h):</strong> {{ director_data.count_24h }}</p>
        <p><strong>New items (7d):</strong> {{ director_data.count_7d }}</p>

        {% if director_data.mentions %}
        <h4>Top Items</h4>
        {% for mention in director_data.mentions %}
        <div class="mention-item {{ mention.severity.value }}">
            <h5>
                <a href="{{ mention.article.url }}" target="_blank">{{ mention.article.title }}</a>
            </h5>
            <p>
                <strong>Source:</strong> {{ mention.article.source }} |
                <strong>Date:</strong> {{ mention.article.published_at or 'Unknown' }} |
                <span class="badge {{ mention.sentiment.value }}">{{ mention.sentiment.value }}</span> |
                <strong>Severity:</strong> {{ mention.severity.value }} |
                <strong>Confidence:</strong> {{ "%.2f"|format(mention.confidence) }}
            </p>
            <p><strong>Category:</strong> {{ mention.category.value }}</p>
            {% if mention.summary_bullets %}
            <ul>
                {% for bullet in mention.summary_bullets %}
                <li>{{ bullet }}</li>
                {% endfor %}
            </ul>
            {% endif %}
            <p><em>{{ mention.why_it_matters }}</em></p>
        </div>
        {% endfor %}
        {% else %}
        <p>No new mentions in the last 24 hours.</p>
        {% endif %}
    </div>
    {% endfor %}

    <h2>Low Confidence Items (Review Queue)</h2>
    {% if low_confidence %}
    <p>Items with confidence < 0.5 require manual review.</p>
    {% for mention in low_confidence %}
    <div class="mention-item">
        <p><strong>{{ mention.director.full_name }}:</strong> {{ mention.article.title }}</p>
        <p>Confidence: {{ "%.2f"|format(mention.confidence) }}</p>
    </div>
    {% endfor %}
    {% else %}
    <p>No low-confidence items.</p>
    {% endif %}
</body>
</html>
"""


def generate_report(report_date: Optional[date] = None) -> Optional[Report]:
    """Generate daily digest report."""
    if not report_date:
        report_date = date.today()
    
    db: Session = SessionLocal()
    try:
        # Check if report already exists
        existing = db.query(Report).filter(Report.report_date == report_date).first()
        if existing:
            logger.info(f"Report for {report_date} already exists")
            return existing

        # Get date range
        date_from = datetime.combine(report_date, datetime.min.time()) - timedelta(days=1)
        date_to = datetime.combine(report_date, datetime.max.time())

        # Get all mentions in date range
        mentions = (
            db.query(Mention)
            .join(Mention.article)
            .filter(
                Mention.created_at >= date_from,
                Mention.created_at <= date_to,
                Mention.is_confirmed == True,
            )
            .order_by(Mention.severity.desc(), Mention.confidence.desc())
            .all()
        )

        # Get directors
        directors = db.query(Director).filter(Director.is_active == True).all()

        # Build stats
        stats = {
            "total_mentions": len(mentions),
            "high_severity": len([m for m in mentions if m.severity == Severity.HIGH]),
            "medium_severity": len([m for m in mentions if m.severity == Severity.MEDIUM]),
            "low_severity": len([m for m in mentions if m.severity == Severity.LOW]),
            "positive": len([m for m in mentions if m.sentiment == Sentiment.POSITIVE]),
            "negative": len([m for m in mentions if m.sentiment == Sentiment.NEGATIVE]),
            "neutral": len([m for m in mentions if m.sentiment == Sentiment.NEUTRAL]),
            "mixed": len([m for m in mentions if m.sentiment == Sentiment.MIXED]),
        }

        # Build director data
        directors_data = []
        for director in directors:
            director_mentions = [m for m in mentions if m.director_id == director.id]
            mentions_24h = [
                m
                for m in director_mentions
                if m.created_at >= datetime.utcnow() - timedelta(days=1)
            ]
            mentions_7d = [
                m
                for m in director_mentions
                if m.created_at >= datetime.utcnow() - timedelta(days=7)
            ]

            directors_data.append(
                {
                    "director": director,
                    "mentions": mentions_24h[:20],  # Top 20
                    "count_24h": len(mentions_24h),
                    "count_7d": len(mentions_7d),
                }
            )

        # Low confidence items
        low_confidence = [m for m in mentions if m.confidence < 0.5 and not m.is_reviewed]

        # Render HTML
        template = Template(REPORT_TEMPLATE)
        html_content = template.render(
            company_name=settings.company_name,
            report_date=report_date.isoformat(),
            generated_at=datetime.utcnow().isoformat(),
            stats=stats,
            directors_data=directors_data,
            low_confidence=low_confidence[:50],  # Limit to 50
        )

        # Save HTML
        os.makedirs(settings.local_storage_dir, exist_ok=True)
        html_filename = f"report_{report_date.isoformat()}.html"
        html_path = os.path.join(settings.local_storage_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Generate PDF
        pdf_filename = f"report_{report_date.isoformat()}.pdf"
        pdf_path = os.path.join(settings.local_storage_dir, pdf_filename)
        HTML(string=html_content).write_pdf(pdf_path)

        # Create report record
        report = Report(
            report_date=report_date,
            html_path=html_path,
            pdf_path=pdf_path,
            stats=stats,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(f"Generated report for {report_date}: {html_path}")

        # Send email (async, but we'll call it synchronously for now)
        try:
            import asyncio

            report_url = f"http://localhost:8000/api/reports/{report.id}/html"  # Adjust based on deployment
            asyncio.run(send_daily_digest(report_date, report_url))
        except Exception as e:
            logger.error(f"Error sending email: {e}")

        return report
    finally:
        db.close()

