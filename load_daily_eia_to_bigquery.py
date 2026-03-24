from __future__ import annotations

import os
from datetime import date, timedelta

import pandas as pd
import pandas_gbq
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from eia_api import fetch_daily_fuel, fetch_daily_region

# -----------------------------
# Configuration
# -----------------------------
PROJECT_ID = "sipa-adv-c-purple-flamingo"
DATASET_ID = "eia_data"

FUEL_TABLE_ID = "daily_fuel_main"
REGION_TABLE_ID = "daily_region_main"

LOOKBACK_DAYS = 90

# Read from local environment
EIA_API_KEY = os.getenv("EIA_API_KEY")


# -----------------------------
# Helpers
# -----------------------------
def get_date_window() -> tuple[str, str]:
    """
    Rolling window for the last 90 days, ending today.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    return start_date.isoformat(), end_date.isoformat()


def ensure_dataset_exists(
    client: bigquery.Client, project_id: str, dataset_id: str
) -> None:
    dataset_ref = bigquery.Dataset(f"{project_id}.{dataset_id}")
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset already exists: {project_id}.{dataset_id}")
    except NotFound:
        client.create_dataset(dataset_ref)
        print(f"Created dataset: {project_id}.{dataset_id}")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Rename API column names to BigQuery-friendly snake_case.
    """
    rename_map = {
        "respondent-name": "respondent_name",
        "type-name": "type_name",
        "value-units": "value_units",
    }
    return df.rename(columns=rename_map)


def clean_common_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standard cleaning shared across both daily fuel and daily region tables.
    """
    df = df.copy()

    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    if "period" in df.columns:
        # Keep as date for easier filtering in BigQuery and Streamlit
        df["period"] = pd.to_datetime(df["period"], errors="coerce").dt.date

    if "timezone" in df.columns:
        df["timezone"] = df["timezone"].astype("string")

    df["loaded_at"] = pd.Timestamp.utcnow()

    return df


# -----------------------------
# Extractors
# -----------------------------
def extract_daily_fuel(api_key: str, start: str, end: str) -> pd.DataFrame:
    """
    Pull daily fuel-type data from EIA and keep the columns the fuel app may need.
    """
    rows = fetch_daily_fuel(api_key, start, end)
    df = pd.json_normalize(rows)

    if df.empty:
        return df

    desired_columns = [
        "period",
        "respondent",
        "respondent-name",
        "type",
        "type-name",
        "timezone",
        "value",
        "value-units",
    ]
    existing_columns = [c for c in desired_columns if c in df.columns]
    df = df[existing_columns].copy()

    df = normalize_columns(df)
    df = clean_common_types(df)

    return df


def extract_daily_region(api_key: str, start: str, end: str) -> pd.DataFrame:
    """
    Pull daily region demand data from EIA and keep the columns the region app may need.
    """
    rows = fetch_daily_region(api_key, start, end)
    df = pd.json_normalize(rows)

    if df.empty:
        return df

    desired_columns = [
        "period",
        "respondent",
        "respondent-name",
        "timezone",
        "value",
        "value-units",
    ]
    existing_columns = [c for c in desired_columns if c in df.columns]
    df = df[existing_columns].copy()

    df = normalize_columns(df)
    df = clean_common_types(df)

    return df


# -----------------------------
# Loaders
# -----------------------------
def load_table(
    df: pd.DataFrame, project_id: str, dataset_id: str, table_id: str
) -> None:
    """
    Replace the destination table with a fresh 90-day snapshot.
    """
    if df.empty:
        print(f"No rows returned for {table_id}. Skipping upload.")
        return

    destination_table = f"{dataset_id}.{table_id}"

    pandas_gbq.to_gbq(
        dataframe=df,
        destination_table=destination_table,
        project_id=project_id,
        if_exists="replace",
    )

    print(f"Uploaded {len(df)} rows to {project_id}.{destination_table}")


# -----------------------------
# Verification
# -----------------------------
def verify_table(project_id: str, dataset_id: str, table_id: str) -> None:
    table_fqn = f"{project_id}.{dataset_id}.{table_id}"
    sql = f"""
    SELECT
        COUNT(*) AS row_count,
        MIN(period) AS min_period,
        MAX(period) AS max_period,
        MAX(loaded_at) AS latest_load_time
    FROM `{table_fqn}`
    """
    result = pandas_gbq.read_gbq(sql, project_id=project_id)
    print(f"\nVerification for {table_id}:")
    print(result)


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    if not EIA_API_KEY:
        raise ValueError(
            "Missing EIA_API_KEY environment variable. "
            "Set it before running the script."
        )

    start_date, end_date = get_date_window()
    print(f"Refreshing EIA daily data from {start_date} to {end_date}")

    client = bigquery.Client(project=PROJECT_ID)
    ensure_dataset_exists(client, PROJECT_ID, DATASET_ID)

    # Fuel table
    fuel_df = extract_daily_fuel(EIA_API_KEY, start_date, end_date)
    print(f"Fetched {len(fuel_df)} daily fuel rows")
    load_table(fuel_df, PROJECT_ID, DATASET_ID, FUEL_TABLE_ID)
    verify_table(PROJECT_ID, DATASET_ID, FUEL_TABLE_ID)

    # Region table
    region_df = extract_daily_region(EIA_API_KEY, start_date, end_date)
    print(f"Fetched {len(region_df)} daily region rows")
    load_table(region_df, PROJECT_ID, DATASET_ID, REGION_TABLE_ID)
    verify_table(PROJECT_ID, DATASET_ID, REGION_TABLE_ID)


if __name__ == "__main__":
    main()
