"""Settings endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import require_admin
from app.database import get_db
from app.models.setting import Setting

router = APIRouter()


@router.get("/")
def get_settings(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Get all settings."""
    settings = db.query(Setting).all()
    return {s.key: s.value for s in settings}


@router.get("/{key}")
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Get setting by key."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        return {"key": key, "value": None}
    return {"key": setting.key, "value": setting.value}

