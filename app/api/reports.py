"""Report endpoints."""

from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.database import get_db
from app.models.report import Report

router = APIRouter()


@router.get("/")
def list_reports(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List reports."""
    reports = db.query(Report).order_by(Report.report_date.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "report_date": r.report_date.isoformat(),
            "html_path": r.html_path,
            "pdf_path": r.pdf_path,
            "stats": r.stats,
            "created_at": r.created_at.isoformat(),
        }
        for r in reports
    ]


@router.get("/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get report by ID."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": report.id,
        "report_date": report.report_date.isoformat(),
        "html_path": report.html_path,
        "pdf_path": report.pdf_path,
        "stats": report.stats,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/{report_id}/html")
def get_report_html(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get report HTML file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not report.html_path:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report.html_path, media_type="text/html")


@router.get("/{report_id}/pdf")
def get_report_pdf(
    report_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get report PDF file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or not report.pdf_path:
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report.pdf_path, media_type="application/pdf")

