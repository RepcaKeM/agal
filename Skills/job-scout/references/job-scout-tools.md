# Job Scout Tools Reference

Reference of MCP tools available to the `job-scout` skill across Polish job boards and project management.

## 1. Polish Tech Job Hub (`polish-job-hub`)

### `search_nofluffjobs`
- **Description**: Wyszukuje oferty na No Fluff Jobs (przeszukiwanie bazy in-memory z natychmiastową odpowiedzią).
- **Parameters**:
  - `keyword` (`string`): Słowo kluczowe roli/technologii (np. `"python"`, `"react"`, `"devops"`).
  - `location` (`string`): Opcjonalny filtr (np. `"remote"`, `"warszawa"`, `"krakow"`). Puste = wszystkie.
  - `limit` (`integer`): Maksymalna liczba ofert (domyślnie 10).
  - `seniority` (`string`): Poziom (`"junior"`, `"mid"`, `"senior"`, `"expert"`).

### `search_justjoin_it`
- **Description**: Wyszukuje oferty na Just Join IT (parsowanie Schema.org JSON-LD z Next.js SSR).
- **Parameters**:
  - `keyword` (`string`): Słowo kluczowe roli/technologii.
  - `location` (`string`): Filtr lokalizacji (`"remote"` lub nazwa miasta).
  - `limit` (`integer`): Maksymalna liczba ofert (domyślnie 10).

### `search_polish_jobs`
- **Description**: Narzędzie zintegrowane – odpytuje równolegle NoFluffJobs i JustJoinIT z automatyczną deduplikacją.
- **Parameters**:
  - `keyword` (`string`): Słowo kluczowe.
  - `location` (`string`): Lokalizacja (`""` lub `"remote"`).
  - `limit` (`integer`): Łączny limit ofert (domyślnie 10).
  - `source` (`string`): `"all"`, `"nofluffjobs"`, `"justjoinit"`.

**Standard Schema zwróconego obiektu**:
```json
{
  "source": "nofluffjobs | justjoinit",
  "id": "slug-or-id",
  "title": "Senior Python Engineer",
  "company": "Company Name",
  "url": "https://...",
  "location": "Warszawa | Remote",
  "work_mode": "remote | hybrid | office",
  "seniority": "Senior | Mid | Junior",
  "contract_types": ["b2b", "uop"],
  "salary_min": 18000.0,
  "salary_max": 24000.0,
  "salary_currency": "PLN",
  "salary_period": "month | hour",
  "salary_display": "B2B: 18000–24000 PLN/m-c",
  "skills": ["Python", "FastAPI", "Docker"]
}
```

---

## 2. LinkedIn MCP (`linkedin`)

### `search_jobs`
- Parameters: `keywords`, `location`, `work_type` (`"remote"`, `"hybrid"`, `"on_site"`), `sort_by` (`"date"`), `date_posted` (`"past_week"`), `max_pages`.
- Returns: list of jobs with `id`, `title`, `company`, `location`, `url`.

### `get_job_details`
- Parameters: `job_id`.
- Returns: detailed description, skills, salary insights (if disclosed).

---

## 3. Apify MCP (`apify`)

Uruchamiany jako zdalny serwer HTTP MCP (`https://mcp.apify.com/?tools=actors,docs,memo23/pracuj-scraper`):
- Udostępnia narzędzia `call-actor`, `search-actors`, `fetch-actor-details` oraz dedykowany aktor `memo23/pracuj-scraper`.
- Uwierzytelnianie następuje przez przeglądarkę (OAuth) przy pierwszym połączeniu lub przez token Apify.
- Jeśli serwer nie jest połączony, narzędzie jest omijane (graceful degradation).

---

## 4. itsaplan Project Management (`itsaplan`)

- `get_project`: `project_id: "LEAD"` → pobiera kolumny, pola niestandardowe i etykiety.
- `list_issues`: `project_id: "LEAD"` → pobiera istniejące zgłoszenia (sprawdzanie duplikatów).
- `create_issue`: `project_id: "LEAD"`, `columnId`, `title`, `customFields: {"oferta": url, "Budżet": number}`, `labelIds`, `description`.
