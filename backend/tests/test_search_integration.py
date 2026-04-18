"""Integration-style test: run_search with mocked PRH client."""

from __future__ import annotations

from datetime import date

import pytest

from app.config import clear_config_cache
from app.services.prh_client import PrhClient
from app.services.search_service import run_search
from app.models.api_schemas import SearchMode


def _fake_prh_company() -> dict:
    """Minimal YTJ-shaped payload for Lappeenranta + ICT."""
    return {
        "businessId": {"value": "1234567-8", "source": "1"},
        "registrationDate": "2025-06-01",
        "lastModified": "2025-06-15T10:00:00",
        "names": [
            {
                "name": "Testisoft Oy",
                "type": "1",
                "version": 1,
                "source": "1",
            }
        ],
        "mainBusinessLine": {
            "type": "62010",
            "descriptions": [{"languageCode": "1", "description": "Ohjelmistojen suunnittelu"}],
            "source": "1",
        },
        "addresses": [
            {
                "type": 1,
                "postOffices": [
                    {"city": "Lappeenranta", "languageCode": "1", "municipalityCode": "405"},
                ],
                "source": "1",
            }
        ],
        "tradeRegisterStatus": "1",
        "status": "1",
    }


@pytest.fixture
def fake_region(monkeypatch):
    clear_config_cache()

    def _cfg():
        return {
            "region_name_fi": "Test",
            "fetch_limits": {"max_pages_per_location": 5},
            "municipalities": [
                {"code": "405", "name_fi": "Lappeenranta", "location_query": "Lappeenranta"},
            ],
        }

    monkeypatch.setattr("app.services.search_service.get_region_config", _cfg)


def test_run_search_returns_company(monkeypatch, fake_region):
    def _iter(self, *, location, registration_date_start, registration_date_end, max_pages=500):
        assert location == "Lappeenranta"
        return [_fake_prh_company()]

    monkeypatch.setattr(PrhClient, "iter_companies_for_location", _iter)

    res = run_search(date_from=date(2025, 1, 1), mode=SearchMode.new_or_changed)
    assert res.total_after_filter >= 1
    assert any(c.business_id == "1234567-8" for c in res.companies)
    assert res.progress_log
    assert any("Lappeenranta" in line for line in res.progress_log)


def test_run_search_respects_date_filter(monkeypatch, fake_region):
    old = _fake_prh_company()
    old["registrationDate"] = "2020-01-01"
    old["lastModified"] = "2020-01-01T00:00:00"

    def _iter(self, **kwargs):
        return [old]

    monkeypatch.setattr(PrhClient, "iter_companies_for_location", _iter)

    res = run_search(date_from=date(2025, 1, 1), mode=SearchMode.new_only)
    assert res.total_after_filter == 0
