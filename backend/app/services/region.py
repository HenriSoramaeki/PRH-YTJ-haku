"""South Karelia municipality allowlist and address matching."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.config import get_region_config


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def municipality_allowlist() -> tuple[set[str], set[str]]:
    """Returns (municipality_codes, normalized_city_names)."""
    cfg = get_region_config()
    muni = cfg.get("municipalities") or []
    codes: set[str] = set()
    names: set[str] = set()
    for row in muni:
        code = str(row.get("code", "")).strip()
        if code:
            codes.add(code.zfill(3))
        for key in ("name_fi", "name_sv", "location_query"):
            v = row.get(key)
            if isinstance(v, str) and v.strip():
                names.add(_norm(v))
    return codes, names


def company_in_region(company: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    """
    Returns (is_match, municipality_name, municipality_code) from first matching address.
    """
    codes_ok, names_ok = municipality_allowlist()
    addresses = company.get("addresses") or []
    for addr in addresses:
        for po in addr.get("postOffices") or []:
            code = po.get("municipalityCode")
            city = po.get("city") or ""
            if code and str(code).strip().zfill(3) in codes_ok:
                return True, city or None, str(code).strip().zfill(3)
            if city and _norm(city) in names_ok:
                return True, city, str(code).strip().zfill(3) if code else None
    return False, None, None
