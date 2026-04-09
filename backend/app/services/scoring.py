"""ICT relevance scoring: keyword lists + fuzzy partial matching."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from rapidfuzz import fuzz

from app.config import get_keywords_config


def _norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[\s_\-/]+", " ", s)
    return s.strip()


def _token_variants(token: str) -> list[str]:
    t = token.strip()
    if not t:
        return []
    return list({_norm_text(t), _norm_text(t.replace(" ", ""))})


@dataclass
class ScoreResult:
    score: float
    matches: list[dict[str, Any]]


@dataclass
class ExcludeResult:
    excluded: bool
    reason: str | None = None


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def company_excluded_from_ict(
    *,
    name: str,
    business_line: str,
    all_names: list[str],
    tol_code: str | None,
) -> ExcludeResult:
    """
    Poista selvästi ei-ICT yritykset (leipomo, ravintola, rakennus jne.).
    Tarkistaa TOL-koodin prefiksit ja exclude-avainsanat nimessä / toimialatekstissä.
    """
    cfg = get_keywords_config()
    tc = (tol_code or "").strip()

    tol_ex = cfg.get("exclude_tol_prefixes") or []
    for pref in tol_ex:
        p = str(pref).strip()
        if p and tc.startswith(p):
            return ExcludeResult(excluded=True, reason=f"TOL:{p}*")

    terms_cfg = cfg.get("exclude_keywords") or []
    exclude_terms: list[tuple[str, float]] = []
    for item in terms_cfg:
        if isinstance(item, dict):
            kw = str(item.get("term", "")).strip()
            wt = float(item.get("weight", 1.0))
        else:
            kw = str(item).strip()
            wt = 1.0
        if kw:
            exclude_terms.append((kw, wt))

    if not exclude_terms:
        return ExcludeResult(excluded=False)

    ex_threshold = float(cfg.get("exclude_fuzzy_threshold", 90))
    partial_weight = float(cfg.get("exclude_partial_ratio_weight", cfg.get("partial_ratio_weight", 0.92)))

    fields_raw = cfg.get("exclude_match_fields") or ["business_line", "name", "all_names"]
    blob_parts: list[str] = []
    if "business_line" in fields_raw:
        blob_parts.append(business_line)
    if "name" in fields_raw:
        blob_parts.append(name)
    if "all_names" in fields_raw:
        blob_parts.append(" ".join(all_names))

    combined = _norm_text(" ".join(blob_parts))

    for kw, kw_weight in exclude_terms:
        variants = _token_variants(kw)
        if not variants:
            continue
        best = 0.0
        for variant in variants:
            if len(variant) < 3:
                continue
            if variant in combined:
                best = 100.0
                break
            pr = float(fuzz.partial_ratio(variant, combined))
            tr = float(fuzz.token_sort_ratio(variant, combined))
            s = max(pr, tr * partial_weight) * kw_weight
            best = max(best, min(100.0, s))
        if best >= ex_threshold:
            return ExcludeResult(excluded=True, reason=f"ei-ICT:{kw}")

    return ExcludeResult(excluded=False)


def score_company_texts(
    *,
    name: str,
    business_line: str,
    extra_text: str,
    website: str,
    all_names: list[str],
    tol_code: str | None = None,
) -> ScoreResult:
    """
    Combine weighted fuzzy scores over configured keyword lists.
    Returns score 0..100 and list of {keyword, field, score}.
    """
    cfg = get_keywords_config()
    weights = cfg.get("weights") or {}
    w_name = float(weights.get("name", 0.35))
    w_line = float(weights.get("business_line", 0.35))
    w_extra = float(weights.get("extra", 0.25))
    w_web = float(weights.get("website", 0.05))

    keywords_cfg = cfg.get("keywords") or []
    keywords: list[tuple[str, float]] = []
    for item in keywords_cfg:
        if isinstance(item, dict):
            kw = str(item.get("term", "")).strip()
            wt = float(item.get("weight", 1.0))
        else:
            kw = str(item).strip()
            wt = 1.0
        if kw:
            keywords.append((kw, wt))

    fuzzy_threshold = float(cfg.get("fuzzy_threshold", 88))
    partial_weight = float(cfg.get("partial_ratio_weight", 0.85))

    fields = {
        "name": _norm_text(name),
        "business_line": _norm_text(business_line),
        "extra": _norm_text(extra_text),
        "website": _norm_text(website),
        "all_names": _norm_text(" ".join(all_names)),
    }

    per_field_best: dict[str, float] = {k: 0.0 for k in fields}
    matches: list[dict[str, Any]] = []

    for kw, kw_weight in keywords:
        variants = _token_variants(kw)
        if not variants:
            continue
        best_kw_score = 0.0
        best_field = "name"
        for field_key, field_text in fields.items():
            if not field_text:
                continue
            for variant in variants:
                if len(variant) < 2:
                    continue
                if variant in field_text:
                    s = 100.0
                else:
                    pr = float(fuzz.partial_ratio(variant, field_text))
                    tr = float(fuzz.token_sort_ratio(variant, field_text))
                    s = max(pr, tr * partial_weight)
                    if s < fuzzy_threshold:
                        continue
                s = min(100.0, s * kw_weight)
                if s > best_kw_score:
                    best_kw_score = s
                    best_field = field_key
        if best_kw_score > 0:
            matches.append(
                {
                    "keyword": kw,
                    "field": best_field,
                    "score": round(min(100.0, best_kw_score), 1),
                }
            )
            per_field_best[best_field] = max(per_field_best[best_field], best_kw_score)

    # TOL ICT prefix boost (Statistics Finland TOL 2008 code, e.g. 62xxx)
    tol_prefixes = cfg.get("tol_ict_prefixes") or []
    tc = (tol_code or "").strip()
    for pref in tol_prefixes:
        p = str(pref).strip()
        if p and tc.startswith(p):
            per_field_best["business_line"] = max(per_field_best["business_line"], 95.0)
            matches.append(
                {
                    "keyword": f"TOL:{pref}",
                    "field": "business_line",
                    "score": 95.0,
                }
            )

    # Weighted aggregate
    name_score = max(per_field_best["name"], per_field_best["all_names"])
    agg = (
        w_name * name_score
        + w_line * per_field_best["business_line"]
        + w_extra * max(per_field_best["extra"], 0.0)
        + w_web * per_field_best["website"]
    )
    denom = w_name + w_line + w_extra + w_web
    base = agg / denom if denom else 0.0

    # Slight boost if multiple distinct keywords hit
    distinct = len({m["keyword"] for m in matches})
    bonus = min(10.0, distinct * 2.0)
    final = _clamp01((base + bonus) / 100.0) * 100.0

    # Dedupe matches by keyword keeping max score
    by_kw: dict[str, dict[str, Any]] = {}
    for m in matches:
        k = m["keyword"]
        if k not in by_kw or m["score"] > by_kw[k]["score"]:
            by_kw[k] = m
    match_list = sorted(by_kw.values(), key=lambda x: -x["score"])

    return ScoreResult(score=round(min(100.0, final), 1), matches=match_list[:20])


def combined_blob_from_tol(mbl: dict[str, Any]) -> str:
    parts: list[str] = []
    t = mbl.get("type")
    if t:
        parts.append(str(t))
    cs = mbl.get("typeCodeSet")
    if cs:
        parts.append(str(cs))
    return " ".join(parts)


def build_company_texts(company: dict[str, Any]) -> dict[str, str | list[str]]:
    """Extract human-readable strings from PRH company JSON."""
    names: list[str] = []
    for n in company.get("names") or []:
        if isinstance(n, dict) and n.get("name"):
            names.append(str(n["name"]))
    primary = names[0] if names else ""

    line_parts: list[str] = []
    mbl = company.get("mainBusinessLine") or {}
    for d in mbl.get("descriptions") or []:
        if isinstance(d, dict) and d.get("description"):
            line_parts.append(str(d["description"]))
    line = " ".join(line_parts)

    web = ""
    w = company.get("website") or {}
    if isinstance(w, dict) and w.get("url"):
        web = str(w["url"])

    extra_bits: list[str] = []
    for cf in company.get("companyForms") or []:
        for d in (cf.get("descriptions") or []):
            if isinstance(d, dict) and d.get("description"):
                extra_bits.append(str(d["description"]))
    for addr in company.get("addresses") or []:
        if addr.get("freeAddressLine"):
            extra_bits.append(str(addr["freeAddressLine"]))

    extra = " ".join(extra_bits)
    # Include combined name blob for auxiliary / parallel names
    blob = _norm_text(" ".join(names) + " " + line + " " + extra + " " + web + " " + combined_blob_from_tol(mbl))
    return {
        "primary_name": primary,
        "all_names": names,
        "business_line": line,
        "website": web,
        "extra": extra + " " + combined_blob_from_tol(mbl),
        "combined": blob,
    }
