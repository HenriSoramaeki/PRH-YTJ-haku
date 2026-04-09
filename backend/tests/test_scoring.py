"""Unit tests for ICT keyword scoring."""

from __future__ import annotations

import pytest

from app.config import clear_config_cache
from app.services.scoring import company_excluded_from_ict, score_company_texts


def test_exact_keyword_in_name_boosts_score(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "fuzzy_threshold": 80,
            "partial_ratio_weight": 0.9,
            "weights": {
                "name": 0.4,
                "business_line": 0.35,
                "extra": 0.2,
                "website": 0.05,
            },
            "tol_ict_prefixes": [],
            "keywords": [{"term": "ohjelmisto", "weight": 1.0}],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    r = score_company_texts(
        name="Esimerkki Ohjelmisto Oy",
        business_line="Muu liiketoiminta",
        extra_text="",
        website="",
        all_names=["Esimerkki Ohjelmisto Oy"],
        tol_code=None,
    )
    assert r.score >= 30.0
    assert any(m["keyword"] == "ohjelmisto" for m in r.matches)


def test_tol_ict_prefix_match(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "fuzzy_threshold": 99,
            "partial_ratio_weight": 0.9,
            "weights": {
                "name": 0.4,
                "business_line": 0.35,
                "extra": 0.2,
                "website": 0.05,
            },
            "tol_ict_prefixes": ["62"],
            "keywords": [],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    r = score_company_texts(
        name="Geneerinen Oy",
        business_line="Tietojenkäsittely, palvelut",
        extra_text="",
        website="",
        all_names=["Geneerinen Oy"],
        tol_code="62010",
    )
    assert r.score >= 30.0
    assert any(m["keyword"].startswith("TOL:") for m in r.matches)


def test_fuzzy_partial_match_english(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "fuzzy_threshold": 85,
            "partial_ratio_weight": 0.92,
            "weights": {
                "name": 0.4,
                "business_line": 0.35,
                "extra": 0.2,
                "website": 0.05,
            },
            "tol_ict_prefixes": [],
            "keywords": [{"term": "software", "weight": 1.0}],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    r = score_company_texts(
        name="Acme SoftWare Solutions",
        business_line="Muu liiketoiminta",
        extra_text="",
        website="",
        all_names=["Acme SoftWare Solutions"],
        tol_code=None,
    )
    assert r.score >= 30.0
    assert any(m["keyword"] == "software" for m in r.matches)


def test_no_match_low_score(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "fuzzy_threshold": 95,
            "partial_ratio_weight": 0.9,
            "weights": {
                "name": 0.4,
                "business_line": 0.35,
                "extra": 0.2,
                "website": 0.05,
            },
            "tol_ict_prefixes": [],
            "keywords": [{"term": "ohjelmisto", "weight": 1.0}],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    r = score_company_texts(
        name="Ravintola Kala Oy",
        business_line="Ravintolatoiminta",
        extra_text="",
        website="",
        all_names=["Ravintola Kala Oy"],
        tol_code="56101",
    )
    assert r.score < 25.0


def test_exclude_restaurant_by_keyword(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "exclude_fuzzy_threshold": 90,
            "exclude_partial_ratio_weight": 0.92,
            "exclude_keywords": [{"term": "ravintola", "weight": 1.0}],
            "exclude_tol_prefixes": [],
            "exclude_match_fields": ["business_line", "name", "all_names"],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    e = company_excluded_from_ict(
        name="Kala Oy",
        business_line="Ravintolatoiminta",
        all_names=["Kala Oy"],
        tol_code="56101",
    )
    assert e.excluded
    assert e.reason is not None


def test_exclude_not_applied_to_ict_company(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "exclude_fuzzy_threshold": 90,
            "exclude_partial_ratio_weight": 0.92,
            "exclude_keywords": [{"term": "ravintola", "weight": 1.0}],
            "exclude_tol_prefixes": [],
            "exclude_match_fields": ["business_line", "name", "all_names"],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    e = company_excluded_from_ict(
        name="Data Oy",
        business_line="Ohjelmistojen suunnittelu",
        all_names=["Data Oy"],
        tol_code="62010",
    )
    assert not e.excluded


def test_exclude_by_tol_prefix(monkeypatch):
    clear_config_cache()

    def fake_cfg():
        return {
            "exclude_keywords": [],
            "exclude_tol_prefixes": ["561"],
        }

    monkeypatch.setattr("app.services.scoring.get_keywords_config", fake_cfg)

    e = company_excluded_from_ict(
        name="X Oy",
        business_line="Muu toiminta",
        all_names=["X Oy"],
        tol_code="56101",
    )
    assert e.excluded
    assert "TOL:" in (e.reason or "")
