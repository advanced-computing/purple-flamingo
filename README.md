# Purple Flamingo: EIA Grid Demand Dashboard

<a target="_blank" href="https://colab.research.google.com/github/advanced-computing/purple-flamingo">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

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
3. Configure Streamlit secrets for BigQuery access:
   ```toml
   # .streamlit/secrets.toml
   EIA_API_KEY = "LTIKgNRTzB9PyNmYCHTfG8sr3A4h2E1RH6O9Swfi"

   [gcp_service_account]
   type = "service_account"
   project_id = "sipa-adv-c-purple-flamingo"
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "streamlit@sipa-adv-c-purple-flamingo.iam.gserviceaccount.com"
   client_id = "..."
   token_uri = "https://oauth2.googleapis.com/token"

   [bigquery]
   project_id = "sipa-adv-c-purple-flamingo"
   dataset_id = "eia_data"
   fuel_table_id = "daily_fuel_main"
   ```
   
4. If you will run the load script locally, authenticate your user account first:
   ```bash
   gcloud auth application-default login
   export EIA_API_KEY="your_eia_api_key"
   python load_daily_eia_to_bigquery.py
   ```
   The load script defaults to the fuel dataset for this lab. To load the region table instead:
   ```bash
   EIA_DATA_SOURCE=region python load_daily_eia_to_bigquery.py
   ```
   To support both app pages from BigQuery, include both table names in secrets:
   ```toml
   [bigquery]
   project_id = "sipa-adv-c-purple-flamingo"
   dataset_id = "eia_data"
   fuel_table_id = "daily_fuel_main"
   region_table_id = "daily_region_main"
   ```

The repo already ignores `.streamlit/secrets.toml`, so the service account key will not be committed.

## Run the App

```bash
streamlit run main_page.py
```

This opens a two-page app:
- Fuel type demand view (`app.py`)
- Region demand view (`region.py`)

Both analytical pages now read from BigQuery with date filters pushed into SQL so the app only loads the records needed for the selected window.

## Lab 10 Notes

See [`LAB_10.md`](LAB_10.md) for the write-up covering:
- which loading strategy each dataset uses
- why both datasets now live in BigQuery
- the performance changes made to keep page loads fast

## Tests

```bash
pytest -q
```

## BigQuery Load Verification

`load_daily_eia_to_bigquery.py` verifies each load by printing:
- total row count
- minimum and maximum `period`
- latest `loaded_at` timestamp

That gives you a quick way to confirm the refresh worked as intended after upload.

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
