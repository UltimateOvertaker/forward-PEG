
# Forward PEG (India) — Real-Mode Starter (No Mocks)

This starter is **real-mode only**. It never generates demo data.
You maintain two simple CSVs that are *easy to update*:
- `data/seed_sources.csv` — paste official transcript/announcement/presentation links (BSE/NSE/company site).
- `data/pe_snapshots.csv` — optional PE and price snapshots you maintain (weekly or when convenient).

The workflow will:
1) Download each `source_url` from `seed_sources.csv`
2) Extract text (PDFs via pdfminer; HTML via basic tag-strip)
3) Use your **GEMINI_API_KEY** to extract numeric guidance as structured facts
4) Join with your `pe_snapshots.csv`
5) Compute **Forward PEG** and **CFO/PAT (5y cumulative)** (CFO/PAT requires XBRL ingestion, which you can enable later)
6) Publish `data/forward_peg.csv` and deploy the static dashboard to GitHub Pages

> Tip: Start by pasting 3–5 links into `seed_sources.csv` (one per company), then run the workflow.

## One-time setup
1) Create a new GitHub repo and upload this folder structure as-is.
2) Settings → Secrets and variables → Actions → **New repository secret** → `GEMINI_API_KEY`.
3) Open `dashboard/index.html` and replace `USER/REPO` in:
   ```
   window.sampleCsvUrl = "https://raw.githubusercontent.com/USER/REPO/main/data/forward_peg.csv";
   ```
   Commit.
4) Actions → enable workflows → run **ingest-and-build**.

## Files you edit (only these two)
- `data/seed_sources.csv`:
  ```
  company,symbol,source_url,doc_type,as_of_date
  Example Co Ltd,EXAMCO,https://www.bseindia.com/xml-data/corpfiling/AttachLive/abcd1234.pdf,transcript,2025-07-25
  Another Co,ANCO,https://www.nseindia.com/companies-listing/corporate-filings/financial-results?some=link,presentation,2025-08-01
  ```
  - **company** and **symbol** help us group rows
  - **source_url** must be the actual PDF/HTML page with the guidance
  - **doc_type**: transcript | presentation | announcement | interview
  - **as_of_date**: the date of the call/filing (YYYY-MM-DD)

- `data/pe_snapshots.csv` (optional but recommended):
  ```
  symbol,pe,price,as_of_date
  EXAMCO,28.5,1024.50,2025-09-01
  ANCO,20.2,315.00,2025-09-01
  ```
  - Keep this simple; update weekly or whenever you like. The workflow will use the latest row per symbol.

## CFO/PAT (5-year cumulative)
- To keep it real and maintenance-free, the script includes an **optional** XBRL fetcher (`src/xbrl_pull_and_parse.py`).
- To enable it later:
  - Put a list of XBRL links into `data/xbrl_sources.csv`:
    ```
    company,symbol,xbrl_url
    Example Co Ltd,EXAMCO,https://.../financial-results/....xbrl
    ```
  - Uncomment the XBRL step in the workflow (see `.github/workflows/ingest.yml`).

## Limits and compliance
- **Prices/PE**: use your own broker export or delayed sources that you’re allowed to use. Live prices are exchange-licensed.
- **Sources**: always prefer BSE/NSE official filings. The app **deep-links** to `source_url` for traceability.

