# Purple Flamingo: EIA Grid Demand Dashboard

Streamlit dashboard for exploring U.S. electricity demand data from the U.S. Energy Information Administration (EIA).

## Data Source

- EIA Open Data API: `electricity/rto` datasets
- Fuel type page endpoint: `daily-fuel-type-data`
- Region page endpoint: `daily-region-data`
- API docs: https://www.eia.gov/opendata/documentation.php

## Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure `pandera` is available (already included in `requirements.txt`):
   ```bash
   pip install "pandera[pandas]"
   ```
3. Configure your EIA API key in Streamlit secrets:
   ```toml
   # .streamlit/secrets.toml
   EIA_API_KEY = "your_key_here"
   ```

## Run the App

```bash
streamlit run mainPage.py
```

This opens a two-page app:
- Fuel type demand view (`app.py`)
- Region demand view (`region.py`)

## Tests

```bash
pytest -q
```

## Pandera Validation in This Repo

Validation lives in `schemas.py` and is applied in both pages at two stages:

1. Raw API payload validation:
- Checks required columns exist for each page.
- Allows extra columns (`strict=False`) so API field additions do not break the app.

2. Parsed data validation:
- Enforces `period` as datetime-like and `value` as numeric-coercible.
- Invalid rows are dropped for required plotting columns.

Failure behavior is non-blocking by default:
- The app shows `st.warning(...)` with a short validation summary.
- It continues with cleaned data when possible.
- If no usable rows remain after cleaning, the page stops with a warning.

## Troubleshooting

- `No data returned`:
  - Check API key and date range.
- Validation warnings:
  - Usually indicate API schema drift or dirty rows in the selected date window.
  - The app will continue when possible; inspect warnings to see dropped fields/rows.
- Empty chart after warnings:
  - All rows were filtered out by required-column checks, parsing, or timezone filter.

## Project Context

The project investigates grid behavior under stress using EIA demand and generation data, with optional future weather integration (NOAA) for event-based analysis.
