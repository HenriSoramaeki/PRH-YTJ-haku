"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    new_only = "new_only"
    new_or_changed = "new_or_changed"


class ReviewStatusApi(str, Enum):
    relevant = "relevant"
    not_relevant = "not_relevant"
    review_later = "review_later"


class SearchRequest(BaseModel):
    """User search: companies registered or changed after this date (inclusive)."""

    date_from: date = Field(description="Alkupäivä (mukana)")
    mode: SearchMode = Field(default=SearchMode.new_or_changed)


class MatchedKeyword(BaseModel):
    keyword: str
    field: str
    score: float = Field(ge=0, le=100, description="Osittainen osuma / relevanssi")


class CompanyRow(BaseModel):
    business_id: str
    name: str
    registration_date: date | None
    last_modified: datetime | None
    municipality: str | None
    municipality_code: str | None
    main_business_line_code: str | None
    main_business_line_text: str | None
    all_names: list[str] = Field(default_factory=list)
    website: str | None
    ict_score: float = Field(ge=0, le=100)
    matched_keywords: list[MatchedKeyword] = Field(default_factory=list)
    review_status: ReviewStatusApi | None = None
    raw_excerpt: str | None = Field(default=None, description="Lyhyt yhteenveto pisteytykseen käytetyistä teksteistä")


class SearchResponse(BaseModel):
    date_from: date
    mode: SearchMode
    fetched_at: datetime
    companies: list[CompanyRow]
    total_after_filter: int
    errors: list[str] = Field(default_factory=list)
    progress_log: list[str] = Field(
        default_factory=list,
        description="Hakuvaiheet (kunta kerrallaan) — hyödyllinen debugissa ja hitaissa hauissa",
    )


class RegionInfo(BaseModel):
    name: str
    municipalities: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


class ExportRequest(BaseModel):
    """Re-post search result rows for server-side export."""

    companies: list[CompanyRow] = Field(default_factory=list)
