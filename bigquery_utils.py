from __future__ import annotations

import os
from collections.abc import Mapping
from datetime import date
from typing import Any

import google.auth
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account


DEFAULT_DATASET_ID = "eia_data"
DEFAULT_FUEL_TABLE_ID = "daily_fuel_main"
DEFAULT_REGION_TABLE_ID = "daily_region_main"
DEFAULT_PROJECT_ID = "sipa-adv-c-purple-flamingo"


def _mapping_to_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value[key] for key in value}


def get_bigquery_config(secrets: Mapping[str, Any]) -> dict[str, str]:
    config = _mapping_to_dict(secrets.get("bigquery", {}))
    project_id = (
        config.get("project_id")
        or secrets.get("project_id")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
    )

    if not project_id:
        service_account_info = secrets.get("gcp_service_account")
        if service_account_info:
            project_id = _mapping_to_dict(service_account_info).get("project_id")

    if not project_id:
        project_id = DEFAULT_PROJECT_ID

    return {
        "project_id": project_id,
        "dataset_id": config.get("dataset_id", DEFAULT_DATASET_ID),
        "fuel_table_id": config.get("fuel_table_id", DEFAULT_FUEL_TABLE_ID),
        "region_table_id": config.get("region_table_id", DEFAULT_REGION_TABLE_ID),
    }


def get_service_account_info(secrets: Mapping[str, Any]) -> dict[str, Any]:
    service_account_info = secrets.get("gcp_service_account")
    if not service_account_info:
        return {}
    return _mapping_to_dict(service_account_info)


def get_bigquery_client(secrets: Mapping[str, Any]) -> bigquery.Client:
    config = get_bigquery_config(secrets)
    service_account_info = secrets.get("gcp_service_account")

    if service_account_info:
        try:
            credentials = service_account.Credentials.from_service_account_info(
                _mapping_to_dict(service_account_info),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return bigquery.Client(
                project=config["project_id"],
                credentials=credentials,
            )
        except Exception:
            # Fall back to local ADC credentials when the Streamlit PEM is malformed.
            pass

    credentials, detected_project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return bigquery.Client(
        project=config["project_id"] or detected_project,
        credentials=credentials,
    )


def read_fuel_data(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    table_id: str,
    start: str,
    end: str,
    eastern_only: bool = False,
) -> pd.DataFrame:
    table_fqn = f"{project_id}.{dataset_id}.{table_id}"
    timezone_filter = "AND LOWER(timezone) = 'eastern'" if eastern_only else ""
    sql = f"""
    SELECT
        CAST(period AS STRING) AS period,
        type_name,
        SUM(value) AS value
    FROM `{table_fqn}`
    WHERE period BETWEEN @start_date AND @end_date
    {timezone_filter}
    GROUP BY period, type_name
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "start_date", "DATE", date.fromisoformat(start)
            ),
            bigquery.ScalarQueryParameter("end_date", "DATE", date.fromisoformat(end)),
        ]
    )

    return client.query(sql, job_config=job_config).to_dataframe()


def read_region_data(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    table_id: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    table_fqn = f"{project_id}.{dataset_id}.{table_id}"
    sql = f"""
    SELECT
        CAST(period AS STRING) AS period,
        respondent,
        SUM(value) AS value
    FROM `{table_fqn}`
    WHERE period BETWEEN @start_date AND @end_date
      AND LOWER(timezone) = 'eastern'
    GROUP BY period, respondent
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "start_date", "DATE", date.fromisoformat(start)
            ),
            bigquery.ScalarQueryParameter("end_date", "DATE", date.fromisoformat(end)),
        ]
    )

    return client.query(sql, job_config=job_config).to_dataframe()
