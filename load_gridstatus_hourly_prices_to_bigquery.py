from __future__ import annotations

from datetime import date, timedelta

import gridstatus
import pandas as pd
import pandas_gbq
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

# -----------------------------
# Configuration
# -----------------------------
PROJECT_ID = "sipa-adv-c-purple-flamingo"
DATASET_ID = "eia_data"
PRICING_TABLE_ID = "hourly_pricing_main"

LOOKBACK_DAYS = 7

# Trading-hub / zonal locations to keep the table manageable
CAISO_LOCATIONS = ["TH_NP15_GEN-APND", "TH_SP15_GEN-APND", "TH_ZP26_GEN-APND"]
NYISO_LOCATIONS = [
    "CAPITL",
    "CENTRL",
    "DUNWOD",
    "HUD VL",
    "LONGIL",
    "N.Y.C.",
    "NORTH",
    "WEST",
]
ERCOT_LOCATIONS = ["HB_HOUSTON", "HB_NORTH", "HB_SOUTH", "HB_WEST"]


# -----------------------------
# BigQuery helpers
# -----------------------------
def get_date_window() -> tuple[date, date]:
    """
    Rolling 7-day window ending today.
    Gridstatus end dates are usually exclusive, so this pulls from
    start_date through today depending on ISO availability.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=LOOKBACK_DAYS)
    return start_date, end_date


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


def ensure_table_exists(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    table_id: str,
    schema: list[bigquery.SchemaField],
) -> None:
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    try:
        client.get_table(table_ref)
        print(f"Table already exists: {table_ref}")
    except NotFound:
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table)
        print(f"Created table: {table_ref}")


# -----------------------------
# Data cleaning
# -----------------------------
def clean_lmp_frame(df: pd.DataFrame, iso: str) -> pd.DataFrame:
    """
    Standardize gridstatus LMP output across ERCOT, CAISO, and PJM.
    """
    if df.empty:
        return df

    df = df.copy()

    rename_map = {
        "Time": "time",
        "Interval Start": "interval_start",
        "Interval End": "interval_end",
        "Market": "market",
        "Location": "location",
        "Location Type": "location_type",
        "LMP": "lmp",
        "Energy": "energy",
        "Congestion": "congestion",
        "Loss": "loss",
    }

    df = df.rename(columns={c: rename_map.get(c, c) for c in df.columns})

    desired_columns = [
        "time",
        "interval_start",
        "interval_end",
        "market",
        "location",
        "location_type",
        "lmp",
        "energy",
        "congestion",
        "loss",
    ]

    existing_columns = [c for c in desired_columns if c in df.columns]
    df = df[existing_columns].copy()

    for col in ["time", "interval_start", "interval_end"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)

    for col in ["lmp", "energy", "congestion", "loss"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["market", "location", "location_type"]:
        if col in df.columns:
            df[col] = df[col].astype("string")

    df["iso"] = iso
    df["loaded_at"] = pd.Timestamp.utcnow()

    # Reorder columns
    final_columns = [
        "iso",
        "time",
        "interval_start",
        "interval_end",
        "market",
        "location",
        "location_type",
        "lmp",
        "energy",
        "congestion",
        "loss",
        "loaded_at",
    ]

    for col in final_columns:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[final_columns]

    # Drop rows without core values
    df = df.dropna(subset=["interval_start", "location", "lmp"])

    return df


# -----------------------------
# Extractors
# -----------------------------
def fetch_caiso_prices(start_date: date, end_date: date) -> pd.DataFrame:
    caiso = gridstatus.CAISO()

    df = caiso.get_lmp(
        date=start_date.isoformat(),
        end=end_date.isoformat(),
        market="DAY_AHEAD_HOURLY",
        locations=CAISO_LOCATIONS,
    )

    return clean_lmp_frame(df, iso="CAISO")


def fetch_nyiso_prices(start_date: date, end_date: date) -> pd.DataFrame:
    nyiso = gridstatus.NYISO()

    df = nyiso.get_lmp(
        date=start_date.isoformat(),
        end=end_date.isoformat(),
        market="DAY_AHEAD_HOURLY",
        locations=NYISO_LOCATIONS,
        location_type="zone",
    )

    return clean_lmp_frame(df, iso="NYISO")


def fetch_ercot_prices(start_date: date, end_date: date) -> pd.DataFrame:
    ercot = gridstatus.Ercot()

    df = ercot.get_lmp(
        date=start_date.isoformat(),
        end=end_date.isoformat(),
        location_type="settlement point",
    )

    df = clean_lmp_frame(df, iso="ERCOT")

    if "location" in df.columns:
        df = df[df["location"].isin(ERCOT_LOCATIONS)].copy()

    return df


def extract_hourly_prices(start_date: date, end_date: date) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    extractors = [
        ("CAISO", fetch_caiso_prices),
        ("NYISO", fetch_nyiso_prices),
        ("ERCOT", fetch_ercot_prices),
    ]

    for iso_name, extractor in extractors:
        try:
            print(f"Fetching {iso_name} prices...")
            iso_df = extractor(start_date, end_date)
            print(f"Fetched {len(iso_df)} rows for {iso_name}")
            frames.append(iso_df)
        except Exception as exc:
            print(f"WARNING: Failed to fetch {iso_name}: {exc}")

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


# -----------------------------
# Loader
# -----------------------------
def load_table(
    df: pd.DataFrame,
    project_id: str,
    dataset_id: str,
    table_id: str,
) -> None:
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


PRICING_TABLE_SCHEMA = [
    bigquery.SchemaField("iso", "STRING"),
    bigquery.SchemaField("time", "TIMESTAMP"),
    bigquery.SchemaField("interval_start", "TIMESTAMP"),
    bigquery.SchemaField("interval_end", "TIMESTAMP"),
    bigquery.SchemaField("market", "STRING"),
    bigquery.SchemaField("location", "STRING"),
    bigquery.SchemaField("location_type", "STRING"),
    bigquery.SchemaField("lmp", "FLOAT"),
    bigquery.SchemaField("energy", "FLOAT"),
    bigquery.SchemaField("congestion", "FLOAT"),
    bigquery.SchemaField("loss", "FLOAT"),
    bigquery.SchemaField("loaded_at", "TIMESTAMP"),
]


# -----------------------------
# Verification
# -----------------------------
def verify_table(project_id: str, dataset_id: str, table_id: str) -> None:
    table_fqn = f"{project_id}.{dataset_id}.{table_id}"

    sql = f"""
    SELECT
        iso,
        COUNT(*) AS row_count,
        MIN(interval_start) AS min_interval_start,
        MAX(interval_start) AS max_interval_start,
        MAX(loaded_at) AS latest_load_time
    FROM `{table_fqn}`
    GROUP BY iso
    ORDER BY iso
    """

    result = pandas_gbq.read_gbq(sql, project_id=project_id)

    print(f"\nVerification for {table_id}:")
    print(result)


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    start_date, end_date = get_date_window()

    print(f"Refreshing hourly pricing data from {start_date} to {end_date}")

    client = bigquery.Client(project=PROJECT_ID)

    ensure_dataset_exists(client, PROJECT_ID, DATASET_ID)
    ensure_table_exists(
        client,
        PROJECT_ID,
        DATASET_ID,
        PRICING_TABLE_ID,
        PRICING_TABLE_SCHEMA,
    )

    prices_df = extract_hourly_prices(start_date, end_date)

    print(f"Fetched {len(prices_df)} total pricing rows")

    load_table(prices_df, PROJECT_ID, DATASET_ID, PRICING_TABLE_ID)
    verify_table(PROJECT_ID, DATASET_ID, PRICING_TABLE_ID)


if __name__ == "__main__":
    main()
