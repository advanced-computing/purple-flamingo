import pandas as pd


def parse_period_and_value(df: pd.DataFrame) -> pd.DataFrame:
    parsed = df.copy()
    parsed["period"] = pd.to_datetime(parsed["period"], errors="coerce")
    parsed["value"] = pd.to_numeric(parsed["value"], errors="coerce")
    return parsed


def convert_units(
    df: pd.DataFrame, units: str, value_col: str = "value"
) -> tuple[pd.DataFrame, str, str]:
    converted = df.copy()
    if units == "GWh":
        scaled_col = f"{value_col}_gwh"
        converted[scaled_col] = converted[value_col] / 1000.0
        return converted, scaled_col, "Demand (GWh)"
    return converted, value_col, "Demand (MWh)"


def filter_to_timezone(
    df: pd.DataFrame, timezone: str = "eastern", column: str = "timezone"
) -> pd.DataFrame:
    if column not in df.columns:
        return df.copy()
    mask = df[column].astype(str).str.lower().eq(timezone.lower())
    return df[mask].copy()


def top_n_by_total(
    df: pd.DataFrame, group_col: str, value_col: str, top_n: int
) -> pd.DataFrame:
    if top_n < 1:
        raise ValueError("top_n must be at least 1")
    top_groups = df.groupby(group_col)[value_col].sum().nlargest(top_n).index
    return df[df[group_col].isin(top_groups)].copy()
