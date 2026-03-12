from typing import Any

import requests


def fetch_all_pages(
    base_url: str, params: dict[str, Any], timeout: int = 60
) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    offset = 0
    length = params.get("length", 5000)
    query_params = params.copy()

    while True:
        query_params["offset"] = offset
        response = requests.get(base_url, params=query_params, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("response", {}).get("data", [])
        all_rows.extend(rows)
        if len(rows) < length:
            break
        offset += length

    return all_rows

DAILY_FUEL_URL = "https://api.eia.gov/v2/electricity/rto/daily-fuel-type-data/data/"
DAILY_REGION_URL = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"
HOURLY_FUEL_URL = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
HOURLY_REGION_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
 
 
def _base_params(api_key: str, start: str, end: str, frequency: str = "daily") -> dict[str, Any]:
    return {
        "api_key": api_key,
        "frequency": frequency,
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": 0,
        "length": 5000,
    }
 
 
def fetch_daily_fuel(api_key: str, start: str, end: str) -> list[dict[str, Any]]:
    params = _base_params(api_key, start, end, frequency="daily")
    return fetch_all_pages(DAILY_FUEL_URL, params)
 
 
def fetch_daily_region(api_key: str, start: str, end: str) -> list[dict[str, Any]]:
    params = _base_params(api_key, start, end, frequency="daily")
    return fetch_all_pages(DAILY_REGION_URL, params)
 
 
def fetch_hourly_fuel(
    api_key: str,
    start: str,
    end: str,
    respondent: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch hourly fuel-type data, optionally filtered to one respondent/BA."""
    params = _base_params(api_key, start, end, frequency="hourly")
    if respondent:
        params["facets[respondent][]"] = respondent
    return fetch_all_pages(HOURLY_FUEL_URL, params)
 
 
def fetch_hourly_region(
    api_key: str,
    start: str,
    end: str,
    respondent: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch hourly region demand data."""
    params = _base_params(api_key, start, end, frequency="hourly")
    if respondent:
        params["facets[respondent][]"] = respondent
    return fetch_all_pages(HOURLY_REGION_URL, params)