"""Director model."""

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Director(Base):
    """Director model."""

    __tablename__ = "directors"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    # Structured name fields for Indian name patterns
    first_name = Column(String(100))
    middle_names = Column(String(200))  # Can contain multiple middle names
    last_name = Column(String(100))
    aliases = Column(JSON, default=list)  # List of strings
    context_terms = Column(JSON, default=list)  # List of strings
    negative_terms = Column(JSON, default=list)  # List of strings
    known_entities = Column(JSON, default=list)  # List of strings
    # Company metadata for India-specific context
    company_name = Column(String(255))
    company_industry = Column(String(100))  # e.g., "Banking", "Technology", "Pharmaceuticals"
    listed_exchange = Column(String(50))  # NSE, BSE, etc.
    hq_state = Column(String(100))  # Headquarters state
    hq_city = Column(String(100))  # Headquarters city
    # India context profile (pre-populated regulatory/legal terms)
    india_context_profile = Column(JSON, default=dict)  # Auto-populated India-specific terms
    # Provider flags
    provider_gdelt_enabled = Column(Boolean, default=True)
    provider_bing_enabled = Column(Boolean, default=True)
    provider_serpapi_enabled = Column(Boolean, default=False)
    provider_rss_enabled = Column(Boolean, default=False)
    provider_newsdata_enabled = Column(Boolean, default=False)
    provider_newsapi_ai_enabled = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mentions = relationship("Mention", back_populates="director", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Director(id={self.id}, full_name='{self.full_name}')>"

    def get_all_names(self) -> List[str]:
        """Get all names (full name + aliases + structured name patterns)."""
        names = [self.full_name]
        if self.aliases:
            names.extend(self.aliases)
        # Add structured name patterns for Indian name matching
        if self.first_name or self.last_name:
            if self.first_name and self.last_name:
                names.append(f"{self.first_name} {self.last_name}")
                if self.middle_names:
                    names.append(f"{self.first_name} {self.middle_names} {self.last_name}")
            if self.last_name and not self.first_name:
                names.append(self.last_name)
        return names

    def get_all_context_terms(self) -> List[str]:
        """Get all context terms including India-specific ones."""
        terms = list(self.context_terms or [])
        # Add India context profile terms if available
        if self.india_context_profile:
            regulatory = self.india_context_profile.get("regulatory_terms", [])
            legal = self.india_context_profile.get("legal_terms", [])
            terms.extend(regulatory)
            terms.extend(legal)
        # Add company-related terms
        if self.company_name:
            terms.append(self.company_name)
        if self.company_industry:
            terms.append(self.company_industry)
        if self.listed_exchange:
            terms.append(self.listed_exchange)
        return terms

    def get_all_negative_terms(self) -> List[str]:
        """Get all negative terms."""
        return self.negative_terms or []

    def get_india_regulatory_terms(self) -> List[str]:
        """Get India-specific regulatory terms."""
        if self.india_context_profile:
            return self.india_context_profile.get("regulatory_terms", [])
        return []

