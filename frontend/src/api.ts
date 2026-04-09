import type { CompanyRow, SearchMode, SearchResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function parseError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (j && typeof j.detail === "string") return j.detail;
    if (j && typeof j.message === "string") return j.message;
  } catch {
    /* ignore */
  }
  return `${res.status} ${res.statusText}`;
}

export async function runSearch(dateFrom: string, mode: SearchMode): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ date_from: dateFrom, mode }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function downloadExport(format: "csv" | "xlsx", companies: CompanyRow[]): Promise<void> {
  const path = format === "csv" ? "/api/export/csv" : "/api/export/xlsx";
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ companies }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition");
  let filename = format === "csv" ? "yritykset.csv" : "yritykset.xlsx";
  if (cd) {
    const m = /filename="?([^";]+)"?/i.exec(cd);
    if (m) filename = m[1];
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
