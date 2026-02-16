"""Email utilities."""

import logging
from typing import List

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings
from app.models.mention import Mention

logger = logging.getLogger(__name__)


async def send_email(to: List[str], subject: str, body_html: str, body_text: str = None):
    """Send email via SMTP."""
    if not settings.smtp_user or not settings.smtp_pass:
        logger.warning("SMTP not configured, logging email instead")
        logger.info(f"Email to {to}: {subject}\n{body_text or body_html}")
        return

    try:
        message = MIMEMultipart("alternative")
        message["From"] = settings.from_email
        message["To"] = ", ".join(to)
        message["Subject"] = subject

        if body_text:
            message.attach(MIMEText(body_text, "plain"))
        message.attach(MIMEText(body_html, "html"))

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_pass,
            use_tls=settings.smtp_use_tls,
        )
        logger.info(f"Email sent to {to}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")


def send_alert_email(mention: Mention):
    """Send immediate alert email for high-severity mention."""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal

    db: Session = SessionLocal()
    try:
        db.refresh(mention, ["director", "article"])

        subject = f"ALERT: {mention.severity.value.upper()} - {mention.director.full_name}"
        body_html = f"""
        <html>
        <body>
            <h2>High Severity Alert</h2>
            <p><strong>Director:</strong> {mention.director.full_name}</p>
            <p><strong>Title:</strong> {mention.article.title}</p>
            <p><strong>Source:</strong> {mention.article.source}</p>
            <p><strong>Date:</strong> {mention.article.published_at or 'Unknown'}</p>
            <p><strong>Severity:</strong> {mention.severity.value.upper()}</p>
            <p><strong>Sentiment:</strong> {mention.sentiment.value}</p>
            <p><strong>Category:</strong> {mention.category.value}</p>
            <p><strong>Confidence:</strong> {mention.confidence:.2f}</p>
            <h3>Summary:</h3>
            <ul>
                {"".join([f"<li>{bullet}</li>" for bullet in mention.summary_bullets])}
            </ul>
            <p><strong>Why it matters:</strong> {mention.why_it_matters}</p>
            <p><a href="{mention.article.url}">Read full article</a></p>
        </body>
        </html>
        """
        body_text = f"""
        High Severity Alert
        
        Director: {mention.director.full_name}
        Title: {mention.article.title}
        Source: {mention.article.source}
        Date: {mention.article.published_at or 'Unknown'}
        Severity: {mention.severity.value.upper()}
        Sentiment: {mention.sentiment.value}
        Category: {mention.category.value}
        Confidence: {mention.confidence:.2f}
        
        Summary:
        {chr(10).join(['- ' + bullet for bullet in mention.summary_bullets])}
        
        Why it matters: {mention.why_it_matters}
        
        Read full article: {mention.article.url}
        """

        import asyncio

        asyncio.run(send_email(settings.recipients_md_list, subject, body_html, body_text))
    finally:
        db.close()


async def send_daily_digest(report_date, report_path: str):
    """Send daily digest email with report link."""
    subject = f"Daily Director Media Monitoring Report - {report_date}"
    body_html = f"""
    <html>
    <body>
        <h2>Daily Director Media Monitoring Report</h2>
        <p>Date: {report_date}</p>
        <p>Please find the daily digest report attached.</p>
        <p><a href="{report_path}">View Report</a></p>
    </body>
    </html>
    """
    body_text = f"""
    Daily Director Media Monitoring Report
    
    Date: {report_date}
    
    View Report: {report_path}
    """

    recipients = settings.recipients_md_list + settings.recipients_admin_list
    await send_email(recipients, subject, body_html, body_text)

