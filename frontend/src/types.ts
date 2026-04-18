export type SearchMode = "new_only" | "new_or_changed";

export type ReviewStatusApi = "relevant" | "not_relevant" | "review_later";

export interface MatchedKeyword {
  keyword: string;
  field: string;
  score: number;
}

export interface CompanyRow {
  business_id: string;
  name: string;
  registration_date: string | null;
  last_modified: string | null;
  municipality: string | null;
  municipality_code: string | null;
  main_business_line_code: string | null;
  main_business_line_text: string | null;
  all_names: string[];
  website: string | null;
  ict_score: number;
  matched_keywords: MatchedKeyword[];
  review_status: ReviewStatusApi | null;
  raw_excerpt: string | null;
}

export interface SearchResponse {
  date_from: string;
  mode: SearchMode;
  fetched_at: string;
  companies: CompanyRow[];
  total_after_filter: number;
  errors: string[];
  progress_log?: string[];
}
