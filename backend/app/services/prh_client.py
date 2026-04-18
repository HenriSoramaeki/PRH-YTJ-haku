"""HTTP client for PRH YTJ open data API v3 (official)."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

PRH_DATE_FMT = "%Y-%m-%d"


class PrhApiError(Exception):
    """Raised when PRH API returns an error or unexpected payload."""


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None


def _parse_date(value: str | None) -> date | None:
    if not value or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class PrhClient:
    """Thin wrapper around GET /companies with pagination and retries."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self._base = (base_url or settings.prh_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.prh_timeout_seconds
        self._max_retries = settings.prh_max_retries

    def fetch_companies_page(
        self,
        *,
        location: str | None = None,
        registration_date_start: date | None = None,
        registration_date_end: date | None = None,
        page: int = 1,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"page": page}
        if location:
            params["location"] = location
        if registration_date_start:
            params["registrationDateStart"] = registration_date_start.strftime(PRH_DATE_FMT)
        if registration_date_end:
            params["registrationDateEnd"] = registration_date_end.strftime(PRH_DATE_FMT)

        url = f"{self._base}/companies"
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    r = client.get(url, params=params)
                if r.status_code == 429:
                    if attempt >= self._max_retries - 1:
                        raise PrhApiError(
                            "PRH rajapinta palautti liian monta pyyntöä lyhyessä ajassa (429). "
                            "Odota muutama minuutti ja yritä uudelleen."
                        )
                    wait = 2**attempt
                    logger.warning("PRH rate limit 429, retry in %ss", wait)
                    time.sleep(wait)
                    continue
                if r.status_code >= 400:
                    raise PrhApiError(f"PRH HTTP {r.status_code}: {r.text[:500]}")
                return r.json()
            except (httpx.HTTPError, ValueError) as e:
                last_exc = e
                logger.warning("PRH request failed (attempt %s): %s", attempt + 1, e)
                time.sleep(1 + attempt)
        raise PrhApiError(f"PRH request failed after retries: {last_exc}") from last_exc

    def iter_companies_for_location(
        self,
        *,
        location: str,
        registration_date_start: date | None,
        registration_date_end: date | None,
        max_pages: int = 500,
    ) -> list[dict[str, Any]]:
        """Fetch all pages for a location query (100 results per page)."""
        all_rows: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            data = self.fetch_companies_page(
                location=location,
                registration_date_start=registration_date_start,
                registration_date_end=registration_date_end,
                page=page,
            )
            companies = data.get("companies") or []
            if not companies:
                break
            all_rows.extend(companies)
            total = int(data.get("totalResults") or 0)
            if page * 100 >= total:
                break
        return all_rows


def company_last_modified(company: dict[str, Any]) -> datetime | None:
    return _parse_dt(company.get("lastModified"))


def company_registration_date(company: dict[str, Any]) -> date | None:
    return _parse_date(company.get("registrationDate"))


def extract_business_id(company: dict[str, Any]) -> str | None:
    bid = company.get("businessId") or {}
    if isinstance(bid, dict):
        return bid.get("value")
    return None
