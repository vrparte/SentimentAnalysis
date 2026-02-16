"""Director management endpoints."""

from typing import List, Optional

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_serializer
from sqlalchemy.orm import Session

from app.api.auth import get_current_user, require_admin
from app.database import get_db
from app.models.director import Director
from app.models.user import UserRole

router = APIRouter()


class DirectorCreate(BaseModel):
    """Director create schema."""

    full_name: str
    first_name: Optional[str] = None
    middle_names: Optional[str] = None
    last_name: Optional[str] = None
    aliases: List[str] = []
    context_terms: List[str] = []
    negative_terms: List[str] = []
    known_entities: List[str] = []
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    listed_exchange: Optional[str] = None
    hq_state: Optional[str] = None
    hq_city: Optional[str] = None
    provider_gdelt_enabled: bool = True
    provider_bing_enabled: bool = True
    provider_serpapi_enabled: bool = False
    provider_rss_enabled: bool = False
    provider_newsdata_enabled: bool = False
    is_active: bool = True


class DirectorUpdate(BaseModel):
    """Director update schema."""

    full_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    context_terms: Optional[List[str]] = None
    negative_terms: Optional[List[str]] = None
    known_entities: Optional[List[str]] = None
    provider_gdelt_enabled: Optional[bool] = None
    provider_bing_enabled: Optional[bool] = None
    provider_serpapi_enabled: Optional[bool] = None
    provider_rss_enabled: Optional[bool] = None
    is_active: Optional[bool] = None


class DirectorResponse(BaseModel):
    """Director response schema."""

    id: int
    full_name: str
    first_name: Optional[str] = None
    middle_names: Optional[str] = None
    last_name: Optional[str] = None
    aliases: List[str]
    context_terms: List[str]
    negative_terms: List[str]
    known_entities: List[str]
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    listed_exchange: Optional[str] = None
    hq_state: Optional[str] = None
    hq_city: Optional[str] = None
    provider_gdelt_enabled: bool
    provider_bing_enabled: bool
    provider_serpapi_enabled: bool
    provider_rss_enabled: bool
    provider_newsdata_enabled: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info) -> str:
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[DirectorResponse])
def list_directors(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List all directors."""
    directors = db.query(Director).all()
    return directors


@router.get("/{director_id}", response_model=DirectorResponse)
def get_director(
    director_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get director by ID."""
    director = db.query(Director).filter(Director.id == director_id).first()
    if not director:
        raise HTTPException(status_code=404, detail="Director not found")
    return director


@router.post("/", response_model=DirectorResponse)
def create_director(
    director_data: DirectorCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Create new director."""
    director = Director(**director_data.dict())
    db.add(director)
    db.commit()
    db.refresh(director)
    return director


@router.put("/{director_id}", response_model=DirectorResponse)
def update_director(
    director_id: int,
    director_data: DirectorUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Update director."""
    director = db.query(Director).filter(Director.id == director_id).first()
    if not director:
        raise HTTPException(status_code=404, detail="Director not found")

    update_data = director_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(director, key, value)

    db.commit()
    db.refresh(director)
    return director


@router.delete("/{director_id}")
def delete_director(
    director_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin),
):
    """Delete director."""
    director = db.query(Director).filter(Director.id == director_id).first()
    if not director:
        raise HTTPException(status_code=404, detail="Director not found")
    db.delete(director)
    db.commit()
    return {"message": "Director deleted"}

