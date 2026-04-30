# 🔌 Purple Flamingo: Electricity Demand & Price Analytics Dashboard

<a target="_blank" href="https://colab.research.google.com/github/advanced-computing/purple-flamingo">
  <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/>
</a>

End-to-end data pipeline and Streamlit application for analyzing U.S. electricity demand, fuel mix, grid stress, and wholesale power prices using:

- **EIA (Energy Information Administration)** demand and generation data
- **GridStatus** ISO-level price data for CAISO, NYISO, and ERCOT
- **Google BigQuery** for storage, querying, and app performance
- **Streamlit** for interactive visualization

---

## 🚀 Overview

This project builds a full-stack data workflow:

> **APIs → Data Cleaning & Validation → BigQuery → Interactive Streamlit Dashboard**

The application allows users to:

- Explore electricity demand by fuel type
- Compare demand across regions and balancing authorities
- Identify high- and low-demand anomaly periods as a proxy for grid stress
- Analyze how fuel mix changes during anomalous demand periods
- Compare wholesale electricity prices with demand for selected ISOs

---

## 🧭 Data Flow Diagram

```mermaid
flowchart LR

A[EIA API<br/>Daily Fuel + Region Data] --> B[ETL Script<br/>load_daily_eia_to_bigquery.py]
C[GridStatus<br/>Hourly ISO Price Data] --> D[ETL Script<br/>load_gridstatus_hourly_prices_to_bigquery.py]

B --> E[BigQuery<br/>daily_fuel_main]
B --> F[BigQuery<br/>daily_region_main]
D --> G[BigQuery<br/>hourly_pricing_main]

E --> H[Streamlit App<br/>main_page.py]
F --> H
G --> H

H --> I[Fuel Type Demand<br/>app.py]
H --> J[Regional Demand<br/>region.py]
H --> K[Grid Stress Analysis<br/>grid_stress.py]
H --> L[Price-Demand Analysis<br/>price_demand.py]
H --> M[Proposal & Reflections<br/>proposal.py]
```

---

## 🧱 Architecture

### 1. EIA Demand and Generation Pipeline

The EIA pipeline pulls recent electricity data from the EIA Open Data API and loads it into BigQuery.

**Source:** EIA Open Data API, `electricity/rto` datasets

**Tables:**

- `daily_fuel_main`
- `daily_region_main`

**Loader:**

```bash
python load_daily_eia_to_bigquery.py
```

**Strategy:**

- Uses a rolling 90-day window
- Cleans and normalizes API output
- Converts EIA column names into BigQuery-friendly snake case
- Replaces the destination table with each refresh
- Verifies each load using row counts, date ranges, and latest load timestamps

To load the regional demand table instead of the default fuel table:

```bash
EIA_DATA_SOURCE=region python load_daily_eia_to_bigquery.py
```

---

### 2. GridStatus Price Pipeline

The price pipeline uses the `gridstatus` Python package to collect hourly wholesale electricity price data.

**Source:** GridStatus

**ISOs covered:**

- CAISO
- NYISO
- ERCOT

**Table:**

- `hourly_pricing_main`

**Loader:**

```bash
python load_gridstatus_hourly_prices_to_bigquery.py
```

**Strategy:**

- Uses a rolling 7-day price window
- Pulls hourly LMP data
- Keeps selected trading hubs / zones to keep the table manageable
- Standardizes price fields across ISOs
- Stores:
  - LMP
  - energy component
  - congestion component
  - loss component
  - market
  - location
  - interval timestamps
  - ISO name

---

### 3. BigQuery Layer

All app-facing data is served from BigQuery rather than directly from APIs.

```text
project: sipa-adv-c-purple-flamingo
dataset: eia_data
```

Expected tables:

```text
daily_fuel_main
daily_region_main
hourly_pricing_main
```

The app uses a shared BigQuery utility layer to:

- Read Streamlit secrets
- Create authenticated BigQuery clients
- Apply default project, dataset, and table names
- Push date filtering into SQL queries
- Read fuel, region, and price data into pandas dataframes

---

## 📊 Streamlit Application

Run the app with:

```bash
streamlit run main_page.py
```

The app contains five pages:

### 1. Fuel Type Demand (`app.py`)

Shows electricity demand by fuel type.

Features:

- Line or stacked area charts
- Top-N fuel type filtering
- Unit toggle between MWh and GWh
- Optional Eastern timezone filtering
- Data served from BigQuery

---

### 2. Regional Demand (`region.py`)

Shows electricity demand by balancing authority / region.

Features:

- Regional demand trends
- Top-N region filtering
- Regional anomaly detection
- Day-over-day demand changes
- Cross-region demand snapshot for a selected date

---

### 3. Grid Stress & Anomaly Analysis (`grid_stress.py`)

Provides a focused grid stress page using demand anomalies.

Features:

- Z-score anomaly detection
- High-demand and low-demand anomaly labels
- Day-over-day percentage changes
- Fuel mix comparison on anomaly days vs. normal days
- Largest fuel mix shift analysis

---

### 4. Price-Demand Analysis (`price_demand.py`)

Combines GridStatus price data with EIA regional demand data.

Features:

- ISO-level daily price and demand metrics
- Mean or median LMP aggregation
- Dual-axis price and demand time series
- Price-demand scatterplots
- Correlation metrics by ISO

Supported ISOs:

- CAISO
- NYISO
- ERCOT

---

### 5. Project Proposal, Feedback, and Reflections (`proposal.py`)

Documents project evolution, methodological decisions, and feedback from the teaching team.

---

## 🧠 Core Analytics

### Grid Stress Detection

Grid stress is operationalized as unusually high or low total demand.

The app:

1. Aggregates demand by day
2. Calculates day-over-day changes
3. Computes z-scores
4. Flags high- and low-demand anomalies based on a user-selected threshold

Conceptually:

```text
z = (daily demand - mean demand) / standard deviation
```

High-demand anomalies are days above the positive threshold. Low-demand anomalies are days below the negative threshold.

---

### Fuel Mix Shift Analysis

For anomaly periods, the app compares average fuel mix shares on anomalous days against normal days.

This helps answer:

- Which fuel types increase during high-demand periods?
- Which fuel types decline during low-demand periods?
- How does generation composition change under stress?

---

### Price-Demand Analysis

The price-demand page links:

- EIA regional demand data
- GridStatus hourly ISO prices

The app aggregates hourly prices to the daily level, maps EIA respondent codes to ISO names, and compares price and demand over matching dates.

---

## 🗂️ Project Structure

```text
.
├── app.py
├── region.py
├── grid_stress.py
├── price_demand.py
├── proposal.py
├── main_page.py
├── eia_api.py
├── data_utils.py
├── schemas.py
├── bigquery_utils.py
├── load_daily_eia_to_bigquery.py
├── load_gridstatus_hourly_prices_to_bigquery.py
├── LAB_10.md
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
└── workflows/
```

---

## ⚙️ Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/advanced-computing/purple-flamingo.git
cd purple-flamingo
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Key dependencies include:

- `streamlit`
- `pandas`
- `plotly`
- `pandera[pandas]`
- `google-cloud-bigquery`
- `pandas-gbq`
- `gridstatus`
- `pytest`
- `ruff`

---

## 🔐 Configuration

### Streamlit secrets

Create a local secrets file:

```text
.streamlit/secrets.toml
```

Example:

```toml
EIA_API_KEY = "your_eia_api_key_here"

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
region_table_id = "daily_region_main"
pricing_table_id = "hourly_pricing_main"
```

Do **not** commit `.streamlit/secrets.toml`.

---

### Local Google Cloud authentication

If running loaders locally, authenticate with Google Cloud:

```bash
gcloud auth application-default login
```

Then export your EIA API key:

```bash
export EIA_API_KEY="your_eia_api_key_here"
```

---

## 🔄 Running the Data Pipelines

### Load EIA fuel data

```bash
python load_daily_eia_to_bigquery.py
```

### Load EIA regional demand data

```bash
EIA_DATA_SOURCE=region python load_daily_eia_to_bigquery.py
```

### Load GridStatus price data

```bash
python load_gridstatus_hourly_prices_to_bigquery.py
```

---

## ▶️ Running the App

```bash
streamlit run main_page.py
```

The app will read from BigQuery using the configuration in Streamlit secrets.

---

## 🧪 Tests

Run the test suite:

```bash
pytest
```

Or, for quieter output:

```bash
pytest -q
```

---

## 🧹 Linting

Run Ruff:

```bash
ruff check .
```

The repo’s Ruff configuration is stored in `pyproject.toml`.

---

## ⚡ Performance Design

To keep the app responsive:

- App pages read from BigQuery rather than directly from the EIA API
- Date filters are pushed into SQL
- BigQuery clients are cached with `st.cache_resource`
- Query outputs are cached with `st.cache_data`
- EIA tables use a rolling 90-day snapshot
- Price data uses a shorter rolling price window
- Pages include timing captions for performance checks

See `lab_10.md` for notes on BigQuery loading and performance decisions.

---

## ⚠️ Troubleshooting

### No data returned

Check:

- Date range
- EIA API key
- Whether the relevant BigQuery table has been loaded

### BigQuery credential errors

Check:

- `.streamlit/secrets.toml`
- Google Cloud application-default credentials
- Project ID and dataset name
- Service account permissions

### Empty price-demand page

Check that both tables are populated for overlapping dates:

- `daily_region_main`
- `hourly_pricing_main`

The price page requires overlapping dates between ISO price data and EIA regional demand data.

### GridStatus fetch warnings

Some ISO endpoints may fail or be unavailable depending on market, date range, or upstream data availability. The price loader is designed to continue loading other ISOs when one fails.

### Validation warnings

Validation warnings usually indicate missing fields, null values, or unexpected API output. The app attempts to continue with cleaned rows when possible.

---

## 🔮 Future Improvements

Potential next steps:

- Add NOAA weather data for event-based analysis
- Expand ISO coverage to PJM, MISO, SPP, or ISO-NE
- Add explicit data freshness indicators in the app
- Add event-based case studies for heat waves, winter storms, or price spikes

---

## 👥 Team

- Aileen Yang
- Aria Kovalovich
- Chengpu Deng

---

## 💡 Project Framing

This project evolved from an initial exploratory dashboard into a more complete data system for examining electricity demand, grid stress, fuel mix, and wholesale power prices.

The central question is:

> **How does the electricity system behave under stress, and how do prices respond?**

The final application combines policy-relevant energy data, reproducible data engineering, statistical anomaly detection, and interactive visualization.
