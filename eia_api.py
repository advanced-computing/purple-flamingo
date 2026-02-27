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
