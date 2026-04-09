import { useCallback, useMemo, useState } from "react";
import { downloadExport, runSearch } from "./api";
import { mergeReviewsIntoRows, setReviewStatus } from "./reviewStorage";
import type { CompanyRow, ReviewStatusApi, SearchMode } from "./types";

function formatDt(s: string | null): string {
  if (!s) return "—";
  if (s.length >= 10) return s.slice(0, 10);
  return s;
}

function kwSummary(c: CompanyRow): string {
  return c.matched_keywords
    .slice(0, 8)
    .map((m) => `${m.keyword} (${Math.round(m.score)})`)
    .join(", ");
}

export default function App() {
  const defaultDate = useMemo(() => {
    const d = new Date();
    d.setMonth(d.getMonth() - 6);
    return d.toISOString().slice(0, 10);
  }, []);

  const [dateFrom, setDateFrom] = useState(defaultDate);
  const [mode, setMode] = useState<SearchMode>("new_or_changed");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<CompanyRow[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [meta, setMeta] = useState<{ fetchedAt: string; total: number } | null>(null);

  const onSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    setErrors([]);
    try {
      const res = await runSearch(dateFrom, mode);
      setRows(mergeReviewsIntoRows(res.companies));
      setErrors(res.errors ?? []);
      setMeta({ fetchedAt: res.fetched_at, total: res.total_after_filter });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tuntematon virhe");
    } finally {
      setLoading(false);
    }
  }, [dateFrom, mode]);

  const onReview = useCallback((businessId: string, status: ReviewStatusApi) => {
    setReviewStatus(businessId, status);
    setRows((prev) =>
      prev.map((r) => (r.business_id === businessId ? { ...r, review_status: status } : r)),
    );
  }, []);

  const onExport = useCallback(
    async (format: "csv" | "xlsx") => {
      if (!rows.length) return;
      setError(null);
      try {
        await downloadExport(format, rows);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Vienti epäonnistui");
      }
    },
    [rows],
  );

  return (
    <div className="page">
      <header className="header">
        <h1>Etelä-Karjala — ICT-yritykset (YTJ)</h1>
        <p className="lede">
          Hakee PRH:n virallisesta YTJ-rajapinnasta yrityksiä, joiden kotikunta on Etelä-Karjalassa ja jotka ovat
          rekisteröityneet tai päivittyneet valitun päivämäärän jälkeen. Tulokset ovat ehdotuksia — tarkista aina
          lähdejärjestelmästä. Arviot tallentuvat vain tähän selaimeen (ei palvelimelle).
        </p>
      </header>

      <section className="panel">
        <div className="row">
          <label className="field">
            <span>Alkupäivä</span>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="field">
            <span>Hakutila</span>
            <select value={mode} onChange={(e) => setMode(e.target.value as SearchMode)}>
              <option value="new_only">Vain uudet yritykset</option>
              <option value="new_or_changed">Uudet tai muuttuneet</option>
            </select>
          </label>
          <button type="button" className="primary" disabled={loading} onClick={onSearch}>
            {loading ? "Haetaan…" : "Hae uudet yritykset"}
          </button>
        </div>
        {error ? <p className="alert">{error}</p> : null}
        {meta ? (
          <p className="meta">
            Löytyi <strong>{meta.total}</strong> yritystä. Haettu {new Date(meta.fetchedAt).toLocaleString("fi-FI")}.
          </p>
        ) : null}
        {errors.length > 0 ? (
          <div className="warn">
            <strong>Huomioita hausta:</strong>
            <ul>
              {errors.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <section className="panel">
        <div className="row spread">
          <h2>Tulokset</h2>
          <div className="btn-group">
            <button type="button" disabled={!rows.length} onClick={() => onExport("csv")}>
              Vie CSV
            </button>
            <button type="button" disabled={!rows.length} onClick={() => onExport("xlsx")}>
              Vie Excel (XLSX)
            </button>
          </div>
        </div>

        <div className="table-wrap">
          <table className="results">
            <thead>
              <tr>
                <th>ICT-piste</th>
                <th>Y-tunnus</th>
                <th>Nimi</th>
                <th>Kunta</th>
                <th>Rekisteröity</th>
                <th>Muutos (PRH)</th>
                <th>Toimiala</th>
                <th>Avainsanat</th>
                <th>Arvio</th>
                <th>Toiminnot</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.business_id}>
                  <td className="num">{r.ict_score.toFixed(1)}</td>
                  <td className="mono">{r.business_id}</td>
                  <td>
                    <div className="name">{r.name}</div>
                    {r.all_names.length > 1 ? (
                      <div className="sub">Muut nimet: {r.all_names.slice(1, 5).join(" · ")}</div>
                    ) : null}
                  </td>
                  <td>{r.municipality ?? "—"}</td>
                  <td>{formatDt(r.registration_date)}</td>
                  <td className="small">{r.last_modified ? r.last_modified.replace("T", " ").slice(0, 19) : "—"}</td>
                  <td className="small">
                    {r.main_business_line_code ? `${r.main_business_line_code} ` : ""}
                    {r.main_business_line_text ?? ""}
                  </td>
                  <td className="small kw">{kwSummary(r) || "—"}</td>
                  <td>{r.review_status ?? "—"}</td>
                  <td>
                    <div className="btn-group vertical">
                      <button type="button" className="tiny" onClick={() => onReview(r.business_id, "relevant")}>
                        Relevantti
                      </button>
                      <button type="button" className="tiny" onClick={() => onReview(r.business_id, "not_relevant")}>
                        Ei relevantti
                      </button>
                      <button type="button" className="tiny" onClick={() => onReview(r.business_id, "review_later")}>
                        Myöhemmin
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && !loading ? (
            <p className="empty">Ei tuloksia. Valitse päivä ja paina hakunappia.</p>
          ) : null}
        </div>
      </section>

      <footer className="footer">
        <p>
          Lähde: PRH YTJ avoin data (
          <a href="https://avoindata.prh.fi/opendata-ytj-api/v3/schema?lang=fi" target="_blank" rel="noreferrer">
            rajapinta
          </a>
          ). Yksityiset elinkeinonharjoittajat eivät kuulu kaupparekisteriin.
        </p>
      </footer>
    </div>
  );
}
