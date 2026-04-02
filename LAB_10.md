# Lab 10: BigQuery Loading and Performance

## All Data in BigQuery

This project now uses BigQuery for both EIA datasets used by the app:

- `daily_fuel_type_data` -> BigQuery table `eia_data.daily_fuel_main`
- `daily_region_data` -> BigQuery table `eia_data.daily_region_main`

### Data loading strategy by source

#### Fuel type dataset

We use a batch snapshot load.

Why:

- The EIA daily fuel endpoint is append-oriented and updated on a regular cadence rather than streaming continuously into our app.
- Our dashboard only needs a recent rolling analysis window, so a scheduled snapshot is simpler and easier to verify than row-by-row incremental writes.
- Replacing the table with a fresh 90-day extract avoids duplicate rows and keeps the query surface small for Streamlit.

Implementation:

- `load_daily_eia_to_bigquery.py` pulls the last 90 days from the EIA API.
- The data is normalized to snake_case, cleaned, and uploaded to `daily_fuel_main`.
- The script verifies the load by checking row count, min/max `period`, and latest `loaded_at`.

#### Region dataset

We also use a batch snapshot load.

Why:

- The region page was originally reading directly from the EIA API, which made page load time depend on network latency and API pagination.
- Loading the region dataset into BigQuery lets the app query only the selected date window and keeps both analytical pages on the same architecture.
- A rolling snapshot is appropriate here for the same reasons as the fuel dataset: the source is updated periodically, and our app focuses on recent history rather than a full historical warehouse.

Implementation:

- `load_daily_eia_to_bigquery.py` supports `EIA_DATA_SOURCE=region`.
- The region data is cleaned and uploaded to `daily_region_main`.
- The same verification query is used after load.

## Part 5-style middle steps repeated

For each source, we repeat the same ingestion pattern:

1. Extract data from the EIA API for a rolling 90-day window.
2. Normalize column names to BigQuery-friendly snake_case.
3. Parse key fields such as `period` and `value`.
4. Load the cleaned data into BigQuery.
5. Verify the table contents after upload.

## Performance

To keep pages loading within two seconds, we made these changes:

- Moved the region page from direct API reads to BigQuery.
- Pushed date filtering into SQL with `WHERE period BETWEEN @start_date AND @end_date`.
- Cached the BigQuery client with `st.cache_resource`.
- Cached query results with `st.cache_data`.
- Kept the BigQuery tables limited to a recent 90-day snapshot instead of loading a much larger historical table into the app.
- Added page-level timing captions to each Streamlit page so we can confirm load time during testing and screen recording.

## Files changed for this lab

- `app.py`
- `region.py`
- `bigquery_utils.py`
- `README.md`
- `load_daily_eia_to_bigquery.py`
