# Etelä-Karjala ICT — yrityshaku (MVP)

Sisäinen työkalu kunnan virkamiehille: etsii [PRH:n YTJ-avoimen datan](https://avoindata.prh.fi/fi) kautta Etelä-Karjalan kunnissa sijaitsevia yrityksiä, jotka on rekisteröity tai päivitetty valitun päivämäärän jälkeen, ja pisteyttää ne ICT-avainsanoilla (virallinen toimiala, nimet, apunimet, muut tekstikentät).

**Tärkeää:** tulokset ovat ehdotuksia, eivät juridista totuutta. Yksityiset elinkeinonharjoittajat eivät näy kaupparekisteriin perustuvassa YTJ-aineistossa.

## Rakenne

- `backend/` — FastAPI, PRH-asiakas, pisteytys, CSV/XLSX-vienti (ei palvelintietokantaa)
- `frontend/` — React + TypeScript (Vite)
- `backend/config/` — `region.yaml` (kunnat), `keywords.yaml` (ICT-termit, `exclude_keywords` / `exclude_tol_prefixes` ei-ICT -suodatukselle)

## Helppokäyttöinen käynnistys (Windows)

**Tavoite:** yksi kaksoisnapsautus → selain aukeaa → käyttö painikkeilla.

1. Asenna kerran **Python 3.12+** ([python.org](https://www.python.org/downloads/)) ja valitse asennuksessa **Add python.exe to PATH**.
2. Kaksoisnapsauta projektin juuressa tiedostoa **`Käynnistä.bat`**.
3. Ensimmäisellä kerralla skripti luo virtuaaliympäristön, asentaa Python-riippuvuudet ja tarvittaessa pyytää **Node.js**-asennuksen, jotta käyttöliittymä voidaan rakentaa (`frontend/dist`). Jos Nodea ei haluta asentaa, käyttöliittymän voi rakentaa kerran toisella koneella ja kopioida kansion `frontend/dist` mukana.
4. Selain avautuu osoitteeseen **http://127.0.0.1:8000** — sama osoite toimii jatkossa suoraan.
5. **Älä sulje** mustaa ikkunaa, jonka otsikko on **Etelä-Karjala ICT** (palvelin pyörii siinä). Sulje se, kun lopetat työpäivän.

Taustalla FastAPI tarjoaa sekä rajapinnan (`/api/...`) että valmiin käyttöliittymän juureen `/`.

## Paikallinen ajo (kehitys)

### Tausta

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Käyttöliittymä

```bash
cd frontend
npm install
npm run dev
```

Avaa `http://127.0.0.1:5173`. Vite välittää `/api`-kutsut porttiin 8000 (`vite.config.ts`).

### Testit

```bash
cd backend
python -m pytest tests -v
```

## Docker

```bash
docker compose up --build
```

- Käyttöliittymä: `http://localhost:8080` (nginx välittää `/api` → backend)
- API suoraan: `http://localhost:8000` (esim. `GET /api/health`)

**Arviot** (relevantti / ei relevantti / myöhemmin) tallentuvat vain **selaimen localStorageen**, ei palvelimelle.

## Konfiguraatio

- Kopioi `backend/config/examples/` -tiedostot `config/`-hakemistoon ja muokkaa tarvittaessa.
- Ympäristömuuttujat (esim. `.env` backend-hakemistossa):
  - `EK_PRH_BASE_URL` — oletus `https://avoindata.prh.fi/opendata-ytj-api/v3`
  - `EK_CORS_ORIGINS` — pilkuilla erotettu lista, esim. `http://localhost:5173,http://localhost:8080`

## Rajapinta (lyhyt)

| Metodi | Polku | Kuvaus |
|--------|--------|--------|
| GET | `/api/health` | Terveystarkistus |
| GET | `/api/region` | Alueen ja kuntien metatiedot |
| POST | `/api/search` | `{ "date_from": "YYYY-MM-DD", "mode": "new_only" \| "new_or_changed" }` |
| POST | `/api/export/csv` | `{ "companies": [ ... ] }` |
| POST | `/api/export/xlsx` | `{ "companies": [ ... ] }` |

## Hakulogiikka (PRH)

- Käytetään virallista `GET /companies` -endpointia (`location` = kunnan hakemäärä `config/region.yaml`).
- **Vain uudet:** `registrationDateStart` / `registrationDateEnd` rajaavat rekisteröinnit.
- **Uudet tai muuttuneet:** haetaan sivutettuna ilman rekisteröintipäivärajaa ja suodatetaan paikallisesti: `registrationDate >= date_from` **tai** `lastModified >= date_from` (UTC-päivän alku). Suurissa kunnissa tämä voi olla raskas — säädä `fetch_limits.max_pages_per_location` tarvittaessa.

## Lisenssi

Sovelluskoodi: tämän repon lisenssi käyttäjän valinnan mukaan. PRH YTJ -aineisto: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (katso PRH:n avoin data).
