import { useCallback, useMemo, useState } from "react";
import { downloadExport, runSearch } from "./api";
import {
  clearSessionBasicAuth,
  hasSessionBasicAuth,
  setSessionBasicAuth,
} from "./authSession";
import { clearAllReviews, mergeReviewsIntoRows, setReviewStatus } from "./reviewStorage";
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

function monthsAgo(n: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() - n);
  return d.toISOString().slice(0, 10);
}

type SortKey = "score" | "name" | "muni" | "reg" | "mod";

export default function App() {
  const defaultDate = useMemo(() => monthsAgo(6), []);

  const [dateFrom, setDateFrom] = useState(defaultDate);
  const [mode, setMode] = useState<SearchMode>("new_or_changed");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<CompanyRow[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [progressLog, setProgressLog] = useState<string[]>([]);
  const [meta, setMeta] = useState<{ fetchedAt: string; total: number } | null>(null);

  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [nameFilter, setNameFilter] = useState("");
  const [minScore, setMinScore] = useState("");

  const [authUser, setAuthUser] = useState("");
  const [authPass, setAuthPass] = useState("");
  const [authRevision, setAuthRevision] = useState(0);

  const displayedRows = useMemo(() => {
    let list = [...rows];
    const nf = nameFilter.trim().toLowerCase();
    if (nf) {
      list = list.filter((r) => {
        const blob = [r.name, ...r.all_names].join(" ").toLowerCase();
        return blob.includes(nf);
      });
    }
    const min = parseFloat(minScore.replace(",", "."));
    if (minScore.trim() !== "" && !Number.isNaN(min)) {
      list = list.filter((r) => r.ict_score >= min);
    }
    const dir = sortDir === "asc" ? 1 : -1;
    list.sort((a, b) => {
      switch (sortKey) {
        case "score":
          return (a.ict_score - b.ict_score) * dir;
        case "name":
          return a.name.localeCompare(b.name, "fi") * dir;
        case "muni":
          return (a.municipality ?? "").localeCompare(b.municipality ?? "", "fi") * dir;
        case "reg":
          return (a.registration_date ?? "").localeCompare(b.registration_date ?? "", "fi") * dir;
        case "mod":
          return (a.last_modified ?? "").localeCompare(b.last_modified ?? "", "fi") * dir;
        default:
          return 0;
      }
    });
    return list;
  }, [rows, sortKey, sortDir, nameFilter, minScore]);

  const onSort = useCallback(
    (key: SortKey) => {
      if (key === sortKey) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir(key === "score" ? "desc" : "asc");
      }
    },
    [sortKey],
  );

  const sortIndicator = (key: SortKey) => (sortKey === key ? (sortDir === "asc" ? " ▲" : " ▼") : "");

  const onSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    setErrors([]);
    setProgressLog([]);
    try {
      const res = await runSearch(dateFrom, mode);
      setRows(mergeReviewsIntoRows(res.companies));
      setErrors(res.errors ?? []);
      setProgressLog(res.progress_log ?? []);
      setMeta({ fetchedAt: res.fetched_at, total: res.total_after_filter });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Tuntematon virhe";
      setError(msg);
      if (msg.includes("401") || msg.toLowerCase().includes("kirjautuminen")) {
        setError(`${msg} Aseta HTTP Basic -tunnukset alla olevasta paneelista, jos palvelin vaatii niitä.`);
      }
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

  const onClearReviews = useCallback(() => {
    clearAllReviews();
    setRows((prev) => prev.map((r) => ({ ...r, review_status: null })));
  }, []);

  const onSaveAuth = useCallback(() => {
    setSessionBasicAuth(authUser.trim(), authPass);
    setAuthPass("");
    setError(null);
    setAuthRevision((x) => x + 1);
  }, [authUser, authPass]);

  const onClearAuth = useCallback(() => {
    clearSessionBasicAuth();
    setAuthUser("");
    setAuthPass("");
    setAuthRevision((x) => x + 1);
  }, []);

  const sessionHasAuth = useMemo(() => {
    void authRevision;
    return hasSessionBasicAuth();
  }, [authRevision]);

  const onExport = useCallback(
    async (format: "csv" | "xlsx") => {
      if (!rows.length) return;
      setError(null);
      try {
        await downloadExport(format, displayedRows);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Vienti epäonnistui");
      }
    },
    [rows.length, displayedRows],
  );

  return (
    <div className="page">
      <header className="header">
        <h1>Etelä-Karjala — ICT-yritykset (YTJ)</h1>
        <p className="lede">
          Hakee PRH:n virallisesta YTJ-rajapinnasta yrityksiä, joiden kotikunta on Etelä-Karjalassa ja jotka ovat
          rekisteröityneet tai päivittyneet valitun päivämäärän jälkeen. Oletuksena näytetään noin{" "}
          <strong>viimeiset 6 kk</strong> — voit vaihtaa päivän tai käyttää pikavalintoja. Tulokset ovat ehdotuksia —
          tarkista aina lähdejärjestelmästä. Arviot tallentuvat vain tähän selaimeen (localStorage), eivät siirry toiselle
          koneelle.
        </p>
      </header>

      <section className="panel">
        <div className="row wrap">
          <label className="field">
            <span>Alkupäivä</span>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <div className="field">
            <span>Pikavalinta</span>
            <div className="btn-group">
              <button type="button" className="smallbtn" onClick={() => setDateFrom(monthsAgo(6))}>
                6 kk
              </button>
              <button type="button" className="smallbtn" onClick={() => setDateFrom(monthsAgo(3))}>
                3 kk
              </button>
              <button type="button" className="smallbtn" onClick={() => setDateFrom(monthsAgo(1))}>
                1 kk
              </button>
            </div>
          </div>
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
        <p className="hint">
          Haku voi kestää useita minuuttueita (jokainen kunta haetaan PRH:sta erikseen). Älä sulje välilehteä kesken.
        </p>
        {error ? <p className="alert">{error}</p> : null}
        {meta ? (
          <p className="meta">
            Löytyi <strong>{meta.total}</strong> yritystä (kaikki kunnat). Haettu {new Date(meta.fetchedAt).toLocaleString("fi-FI")}.
            {nameFilter.trim() !== "" || (minScore.trim() !== "" && !Number.isNaN(parseFloat(minScore))) ? (
              <>
                {" "}
                Näytössä <strong>{displayedRows.length}</strong> suodatuksen jälkeen.
              </>
            ) : null}
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
        {progressLog.length > 0 ? (
          <details className="progress">
            <summary>Hakuvaiheet ({progressLog.length})</summary>
            <ol>
              {progressLog.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ol>
          </details>
        ) : null}

        <details className="authbox">
          <summary>Palvelimen suojaus (HTTP Basic, valinnainen)</summary>
          <p className="small muted">
            Jos ylläpito on laittanut palvelimelle käyttäjätunnuksen ja salasanan, syötä ne tähän. Ne tallennetaan vain
            tämän selaimen istuntoon (sessionStorage), eivät levylle pysyvästi.
          </p>
          <div className="row wrap">
            <label className="field">
              <span>Käyttäjätunnus</span>
              <input value={authUser} onChange={(e) => setAuthUser(e.target.value)} autoComplete="username" />
            </label>
            <label className="field">
              <span>Salasana</span>
              <input
                type="password"
                value={authPass}
                onChange={(e) => setAuthPass(e.target.value)}
                autoComplete="current-password"
              />
            </label>
            <button type="button" onClick={onSaveAuth}>
              Tallenna istuntoon
            </button>
            <button type="button" onClick={onClearAuth} disabled={!sessionHasAuth}>
              Tyhjennä tunnus
            </button>
          </div>
        </details>
      </section>

      <section className="panel">
        <div className="row spread wrap">
          <h2>Tulokset</h2>
          <div className="btn-group">
            <button type="button" disabled={!rows.length} onClick={() => onExport("csv")}>
              Vie CSV
            </button>
            <button type="button" disabled={!rows.length} onClick={() => onExport("xlsx")}>
              Vie Excel (XLSX)
            </button>
            <button type="button" disabled={!rows.some((r) => r.review_status)} onClick={onClearReviews}>
              Tyhjennä arviot
            </button>
          </div>
        </div>

        <div className="filters row wrap">
          <label className="field">
            <span>Suodata nimeä</span>
            <input
              type="search"
              placeholder="esim. soft tai lappee"
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Min. ICT-piste</span>
            <input
              type="text"
              inputMode="decimal"
              placeholder="esim. 30"
              className="narrow"
              value={minScore}
              onChange={(e) => setMinScore(e.target.value)}
            />
          </label>
        </div>

        <div className="table-wrap">
          <table className="results">
            <thead>
              <tr>
                <th>
                  <button type="button" className="thbtn" onClick={() => onSort("score")}>
                    ICT-piste{sortIndicator("score")}
                  </button>
                </th>
                <th>Y-tunnus</th>
                <th>
                  <button type="button" className="thbtn" onClick={() => onSort("name")}>
                    Nimi{sortIndicator("name")}
                  </button>
                </th>
                <th>
                  <button type="button" className="thbtn" onClick={() => onSort("muni")}>
                    Kunta{sortIndicator("muni")}
                  </button>
                </th>
                <th>
                  <button type="button" className="thbtn" onClick={() => onSort("reg")}>
                    Rekisteröity{sortIndicator("reg")}
                  </button>
                </th>
                <th>
                  <button type="button" className="thbtn" onClick={() => onSort("mod")}>
                    Muutos (PRH){sortIndicator("mod")}
                  </button>
                </th>
                <th>Toimiala</th>
                <th>Avainsanat</th>
                <th>Arvio</th>
                <th>Toiminnot</th>
              </tr>
            </thead>
            <tbody>
              {displayedRows.map((r) => (
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
          {rows.length > 0 && displayedRows.length === 0 ? (
            <p className="empty">Ei riviä suodattimilla — kokeile toista hakua tai tyhjennä suodattimet.</p>
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
