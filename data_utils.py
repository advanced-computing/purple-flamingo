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

# ------------------------------
# Anomaly / grid-stress detection
# ------------------------------
 
def compute_daily_totals(df: pd.DataFrame, value_col: str = "value") -> pd.DataFrame:
    """Sum all fuel types to get total daily demand per period."""
    return (
        df.groupby("period")[value_col]
        .sum()
        .reset_index()
        .rename(columns={value_col: "total_demand"})
        .sort_values("period")
    )
 
 
def detect_demand_anomalies(
    daily_totals: pd.DataFrame,
    z_threshold: float = 1.5,
) -> pd.DataFrame:
    """
    Flag days where total demand is anomalously high or low using z-scores.
 
    Returns the same dataframe with added columns:
        - demand_zscore
        - anomaly_type: 'high' | 'low' | None
    """
    df = daily_totals.copy()
    mean = df["total_demand"].mean()
    std = df["total_demand"].std()
 
    if std == 0:
        df["demand_zscore"] = 0.0
        df["anomaly_type"] = None
        return df
 
    df["demand_zscore"] = (df["total_demand"] - mean) / std
    df["anomaly_type"] = df["demand_zscore"].apply(
        lambda z: "high" if z > z_threshold else ("low" if z < -z_threshold else None)
    )
    return df
 
 
def demand_day_over_day_change(daily_totals: pd.DataFrame) -> pd.DataFrame:
    """Add absolute and percentage day-over-day change columns."""
    df = daily_totals.sort_values("period").copy()
    df["demand_change"] = df["total_demand"].diff()
    df["demand_pct_change"] = df["total_demand"].pct_change() * 100
    return df
 
 
# ------------------------------
# Fuel mix analysis
# ------------------------------
 
def fuel_share_by_day(
    df: pd.DataFrame,
    fuel_col: str = "type-name",
    value_col: str = "value",
) -> pd.DataFrame:
    """
    Compute each fuel type's share (%) of total daily demand.
    Returns a wide dataframe: period × fuel_type = share%.
    """
    agg = (
        df.groupby(["period", fuel_col])[value_col]
        .sum()
        .reset_index()
    )
    totals = agg.groupby("period")[value_col].transform("sum")
    agg["share_pct"] = (agg[value_col] / totals * 100).round(2)
    return agg
 
 
def fuel_mix_on_anomaly_days(
    df: pd.DataFrame,
    anomaly_df: pd.DataFrame,
    fuel_col: str = "type-name",
    value_col: str = "value",
    anomaly_type: str = "high",
) -> pd.DataFrame:
    """
    Return the average fuel mix share on anomaly days vs normal days.
    anomaly_type: 'high' | 'low'
    """
    shares = fuel_share_by_day(df, fuel_col, value_col)
    anomaly_periods = anomaly_df.loc[
        anomaly_df["anomaly_type"] == anomaly_type, "period"
    ]
 
    is_anomaly = shares["period"].isin(anomaly_periods)
    shares["day_type"] = is_anomaly.map({True: f"{anomaly_type}_demand", False: "normal"})
 
    return (
        shares.groupby(["day_type", fuel_col])["share_pct"]
        .mean()
        .reset_index()
        .rename(columns={"share_pct": "avg_share_pct"})
    )
 
 
def largest_fuel_shifts(
    mix_comparison: pd.DataFrame,
    fuel_col: str = "type-name",
    anomaly_label: str = "high_demand",
) -> pd.DataFrame:
    """
    Pivot fuel mix comparison to find biggest shifts between
    anomaly days and normal days. Returns sorted by |shift|.
    """
    pivot = mix_comparison.pivot_table(
        index=fuel_col, columns="day_type", values="avg_share_pct"
    ).reset_index()
 
    normal_col = "normal"
    anomaly_col = anomaly_label
 
    if normal_col not in pivot.columns or anomaly_col not in pivot.columns:
        return pd.DataFrame()
 
    pivot["shift_pct"] = pivot[anomaly_col] - pivot[normal_col]
    return pivot.sort_values("shift_pct", key=abs, ascending=False)
 
 
# ------------------------------
# Stacked chart helpers
# ------------------------------
 
def pivot_for_stacked(
    df: pd.DataFrame,
    period_col: str = "period",
    group_col: str = "type-name",
    value_col: str = "value",
) -> pd.DataFrame:
    """Pivot to wide format suitable for stacked area/bar charts."""
    agg = (
        df.groupby([period_col, group_col])[value_col]
        .sum()
        .reset_index()
    )
    return agg.pivot_table(index=period_col, columns=group_col, values=value_col, fill_value=0).reset_index()