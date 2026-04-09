"""CSV and XLSX export from search result rows."""

from __future__ import annotations

import csv
import io
from typing import Any

from openpyxl import Workbook

from app.models.api_schemas import CompanyRow


def companies_to_rows(companies: list[CompanyRow]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in companies:
        kws = "; ".join(f"{m.keyword} ({m.score})" for m in c.matched_keywords[:15])
        out.append(
            {
                "Y-tunnus": c.business_id,
                "Nimi": c.name,
                "Muut nimet": " | ".join(c.all_names[1:20]) if len(c.all_names) > 1 else "",
                "Kunta": c.municipality or "",
                "Kuntanumero": c.municipality_code or "",
                "Rekisteröity": c.registration_date.isoformat() if c.registration_date else "",
                "Viimeksi muutettu (PRH)": c.last_modified.isoformat() if c.last_modified else "",
                "Toimiala (TOL)": c.main_business_line_code or "",
                "Toimiala (kuvaus)": c.main_business_line_text or "",
                "Verkkosivusto": c.website or "",
                "ICT-piste": c.ict_score,
                "Avainsanat": kws,
                "Arvio (käyttäjä)": c.review_status.value if c.review_status else "",
            }
        )
    return out


def to_csv_bytes(companies: list[CompanyRow]) -> bytes:
    rows = companies_to_rows(companies)
    if not rows:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "Y-tunnus",
                "Nimi",
                "Muut nimet",
                "Kunta",
                "Kuntanumero",
                "Rekisteröity",
                "Viimeksi muutettu (PRH)",
                "Toimiala (TOL)",
                "Toimiala (kuvaus)",
                "Verkkosivusto",
                "ICT-piste",
                "Avainsanat",
                "Arvio (käyttäjä)",
            ]
        )
        return buf.getvalue().encode("utf-8-sig")
    buf = io.StringIO()
    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx_bytes(companies: list[CompanyRow]) -> bytes:
    rows = companies_to_rows(companies)
    wb = Workbook()
    ws = wb.active
    ws.title = "Yritykset"
    headers = (
        list(rows[0].keys())
        if rows
        else [
            "Y-tunnus",
            "Nimi",
            "Muut nimet",
            "Kunta",
            "Kuntanumero",
            "Rekisteröity",
            "Viimeksi muutettu (PRH)",
            "Toimiala (TOL)",
            "Toimiala (kuvaus)",
            "Verkkosivusto",
            "ICT-piste",
            "Avainsanat",
            "Arvio (käyttäjä)",
        ]
    )
    ws.append(headers)
    for r in rows:
        ws.append([r.get(h, "") for h in headers])
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
