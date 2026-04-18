import type { CompanyRow, ReviewStatusApi } from "./types";

const KEY = "ek-ict-reviews";

export function loadReviewMap(): Record<string, ReviewStatusApi> {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return {};
    const j = JSON.parse(raw) as unknown;
    if (typeof j !== "object" || j === null) return {};
    return j as Record<string, ReviewStatusApi>;
  } catch {
    return {};
  }
}

function saveReviewMap(m: Record<string, ReviewStatusApi>): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(m));
  } catch {
    /* quota / private mode */
  }
}

export function setReviewStatus(businessId: string, status: ReviewStatusApi): void {
  const m = loadReviewMap();
  m[businessId] = status;
  saveReviewMap(m);
}

export function mergeReviewsIntoRows(rows: CompanyRow[]): CompanyRow[] {
  const m = loadReviewMap();
  return rows.map((r) => ({
    ...r,
    review_status: m[r.business_id] ?? r.review_status ?? null,
  }));
}

export function clearAllReviews(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
