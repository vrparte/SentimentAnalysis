"""Report model."""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import Column, Integer, String, Date, DateTime, JSON, Index

from app.database import Base


class Report(Base):
    """Report model - daily digest reports."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(Date, nullable=False, unique=True, index=True)
    html_path = Column(String(512))
    pdf_path = Column(String(512))
    stats = Column(JSON)  # Counts, summary stats
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_report_date", "report_date"),
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, report_date={self.report_date})>"

