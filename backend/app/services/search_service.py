"""Orchestrates PRH fetch, regional filter, and scoring."""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from typing import Any

from app.config import get_region_config
from app.models.api_schemas import (
    CompanyRow,
    MatchedKeyword,
    SearchMode,
    SearchResponse,
)
from app.services.prh_client import (
    PrhClient,
    PrhApiError,
    company_last_modified,
    company_registration_date,
    extract_business_id,
)
from app.services.region import company_in_region
from app.services.scoring import build_company_texts, company_excluded_from_ict, score_company_texts

logger = logging.getLogger(__name__)


def _at_start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _passes_date_filter(
    company: dict[str, Any],
    date_from: date,
    mode: SearchMode,
) -> bool:
    reg = company_registration_date(company)
    lm = company_last_modified(company)
    start = _at_start_of_day(date_from)
    if mode == SearchMode.new_only:
        return reg is not None and reg >= date_from
    # new_or_changed: registration or last modification on/after date_from
    if reg is not None and reg >= date_from:
        return True
    if lm is not None and lm >= start:
        return True
    return False


def run_search(
    *,
    date_from: date,
    mode: SearchMode,
) -> SearchResponse:
    cfg = get_region_config()
    limits = cfg.get("fetch_limits") or {}
    max_pages = int(limits.get("max_pages_per_location", 300))

    municipalities = cfg.get("municipalities") or []
    client = PrhClient()
    errors: list[str] = []
    seen: dict[str, dict[str, Any]] = {}
    today = date.today()

    for m in municipalities:
        loc = m.get("location_query") or m.get("name_fi")
        if not loc:
            continue
        try:
            if mode == SearchMode.new_only:
                rows = client.iter_companies_for_location(
                    location=str(loc),
                    registration_date_start=date_from,
                    registration_date_end=today,
                    max_pages=max_pages,
                )
            else:
                rows = client.iter_companies_for_location(
                    location=str(loc),
                    registration_date_start=None,
                    registration_date_end=None,
                    max_pages=max_pages,
                )
        except PrhApiError as e:
            msg = f"{loc}: {e}"
            logger.error(msg)
            errors.append(msg)
            continue

        for c in rows:
            bid = extract_business_id(c)
            if not bid:
                continue
            if bid not in seen:
                seen[bid] = c

    rows_out: list[CompanyRow] = []
    for company in seen.values():
        ok, muni_name, muni_code = company_in_region(company)
        if not ok:
            continue
        if not _passes_date_filter(company, date_from, mode):
            continue

        texts = build_company_texts(company)
        mbl = company.get("mainBusinessLine") or {}
        line_code = mbl.get("type")
        line_code_str = str(line_code) if line_code is not None else None

        excl = company_excluded_from_ict(
            name=texts["primary_name"],
            business_line=texts["business_line"],
            all_names=texts["all_names"],
            tol_code=line_code_str,
        )
        if excl.excluded:
            continue

        sr = score_company_texts(
            name=texts["primary_name"],
            business_line=texts["business_line"],
            extra_text=texts["extra"],
            website=texts["website"],
            all_names=texts["all_names"],
            tol_code=line_code_str,
        )
        line_text = texts["business_line"] or None

        bid = extract_business_id(company) or ""
        excerpt = (texts["combined"][:500] + "…") if len(texts["combined"]) > 500 else texts["combined"]

        rows_out.append(
            CompanyRow(
                business_id=bid,
                name=texts["primary_name"],
                registration_date=company_registration_date(company),
                last_modified=company_last_modified(company),
                municipality=muni_name,
                municipality_code=muni_code,
                main_business_line_code=line_code_str,
                main_business_line_text=line_text,
                all_names=texts["all_names"],
                website=texts["website"] or None,
                ict_score=sr.score,
                matched_keywords=[MatchedKeyword(**m) for m in sr.matches],
                review_status=None,
                raw_excerpt=excerpt,
            )
        )

    rows_out.sort(key=lambda x: (-x.ict_score, x.name or ""))

    return SearchResponse(
        date_from=date_from,
        mode=mode,
        fetched_at=datetime.now(timezone.utc),
        companies=rows_out,
        total_after_filter=len(rows_out),
        errors=errors,
    )
