# U.S. Nursing Home Quality — dashboard

An interactive Streamlit dashboard over CMS nursing-home data: nurse staffing,
30-day hospital readmissions, star ratings, and occupancy across ~14,700
Medicare- & Medicaid-certified facilities.

**Live:** <https://devinb98-healthcare-dashboard-app-58tt5l.streamlit.app/>

## About

This is the public, shareable version of a dashboard I originally built as a
**Streamlit-in-Snowflake** app on top of a pipeline that landed CMS data in
Snowflake (Google Drive → AWS Lambda → Glue → Snowflake). Streamlit-in-Snowflake
apps can't be shared outside a Snowflake account, so this port reads a small,
**pre-aggregated parquet bundled in the repo** — no database, no credentials,
and it stays free and always-on.

## Data

- CMS **Nursing Home Compare** provider file (Oct 2024) — ratings, beds,
  residents/day, nurse staffing hours per resident-day, turnover.
- CMS **SNF Value-Based Purchasing** facility performance (FY 2024) —
  risk-standardized 30-day readmission rates.

`build_data.py` reads those raw CSVs, keeps the needed columns, and writes
`data/facilities.parquet` (~0.8 MB) and `data/state_summary.parquet`. The raw
files are large and public, so they're gitignored; the aggregated parquet is
committed so the app runs anywhere.

## Run locally

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

To rebuild the data slice from the raw CSVs:

```bash
SRC=/path/to/cms/csvs python build_data.py
```

## Deploy

Push to GitHub, then on [share.streamlit.io](https://share.streamlit.io) pick
this repo and `app.py` as the entrypoint. No secrets needed.
