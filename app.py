import time
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from google.api_core.exceptions import GoogleAPIError

from bigquery_utils import get_bigquery_client, get_bigquery_config, read_fuel_data
from data_utils import (
    compute_daily_totals,
    convert_units,
    demand_day_over_day_change,
    detect_demand_anomalies,
    drop_invalid_required_rows,
    fuel_mix_on_anomaly_days,
    largest_fuel_shifts,
    parse_period_and_value,
    top_n_by_total,
)

start_time = time.time()
default_end = date.today()
default_start = default_end - timedelta(days=21)

st.set_page_config(page_title="EIA Fuel Type Demand", layout="wide")
st.title("U.S. Electricity Demand by Fuel Type")
st.caption("Data: U.S. Energy Information Administration (EIA), served from BigQuery")
st.markdown("**Team:** Aileen Yang · Aria Kovalovich · Chengpu Deng")

# -------------------
# Sidebar Control
# -------------------
with st.sidebar:
    st.header("Settings")

    start = st.text_input("Start date (YYYY-MM-DD)", value=default_start.isoformat())
    end = st.text_input("End date (YYYY-MM-DD)", value=default_end.isoformat())
    units = st.radio("Units", ["MWh", "GWh"], horizontal=True)
    top_n = st.slider("Show top N fuel types (by total)", 1, 15, 5)
    filter_eastern = st.checkbox("Filter to Eastern timezone only", value=True)

    st.divider()
    st.subheader("Anomaly Detection")
    z_threshold = st.slider(
        "Z-score threshold for anomaly flagging",
        min_value=0.5,
        max_value=3.0,
        value=1.5,
        step=0.1,
        help="Days where total demand deviates more than this many standard deviations are flagged.",
    )
    anomaly_focus = st.radio(
        "Fuel-mix shift analysis: compare",
        ["high_demand", "low_demand"],
        format_func=lambda x: (
            "High-demand days vs normal"
            if x == "high_demand"
            else "Low-demand days vs normal"
        ),
    )
    chart_type = st.radio("Chart type", ["Line", "Stacked Area"], index=0)


# -------------------
# Data Loading
# -------------------
@st.cache_data(show_spinner=False)
def load_fuel_data(start: str, end: str, eastern_only: bool) -> pd.DataFrame:
    client = get_cached_bigquery_client()
    config = get_bigquery_config(st.secrets)
    raw_df = read_fuel_data(
        client=client,
        project_id=config["project_id"],
        dataset_id=config["dataset_id"],
        table_id=config["fuel_table_id"],
        start=start,
        end=end,
        eastern_only=eastern_only,
    )
    parsed_df = parse_period_and_value(raw_df)
    cleaned_df, _ = drop_invalid_required_rows(
        parsed_df, required_columns=["period", "value", "type_name"]
    )
    return cleaned_df


@st.cache_resource(show_spinner=False)
def get_cached_bigquery_client():
    return get_bigquery_client(st.secrets)


@st.cache_data(show_spinner=False)
def build_main_chart_data(
    df: pd.DataFrame, value_col: str, top_n: int
) -> pd.DataFrame:
    chart_df = df.loc[:, ["period", "type_name", value_col]].rename(
        columns={value_col: "Demand"}
    )
    filtered = top_n_by_total(chart_df, "type_name", "Demand", top_n=top_n)
    return filtered.sort_values("period")


@st.cache_data(show_spinner=False)
def build_anomaly_data(df: pd.DataFrame, value_col: str, z_threshold: float) -> pd.DataFrame:
    daily = compute_daily_totals(df, value_col=value_col)
    daily = demand_day_over_day_change(daily)
    return detect_demand_anomalies(daily, z_threshold=z_threshold)


@st.cache_data(show_spinner=False)
def build_mix_comparison(
    df: pd.DataFrame,
    daily: pd.DataFrame,
    value_col: str,
    anomaly_focus: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mix_comparison = fuel_mix_on_anomaly_days(
        df,
        daily,
        fuel_col="type_name",
        value_col=value_col,
        anomaly_type="high" if anomaly_focus == "high_demand" else "low",
    )
    shifts = largest_fuel_shifts(
        mix_comparison,
        fuel_col="type_name",
        anomaly_label="high_demand" if anomaly_focus == "high_demand" else "low_demand",
    )
    return mix_comparison, shifts


try:
    with st.spinner("Loading data from BigQuery..."):
        df = load_fuel_data(start, end, filter_eastern)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
except GoogleAPIError as exc:
    st.error(f"BigQuery request failed: {exc}")
    st.stop()

if df.empty:
    st.warning("No rows returned from BigQuery for the selected date range.")
    st.stop()

df, ycol, ylabel = convert_units(df, units)
agg_sorted = build_main_chart_data(df, ycol, top_n)

# -------------------
# Plot Graph (Main Demand)
# -------------------
st.subheader("Electricity Demand by Fuel Type")

if chart_type == "Stacked Area":
    fig = px.area(
        agg_sorted,
        x="period",
        y="Demand",
        color="type_name",
        title=f"Electricity demand by fuel type — stacked area ({start} to {end})",
        labels={"period": "Date", "Demand": ylabel, "type_name": "Fuel type"},
    )
    fig.update_traces(mode="lines")
else:
    fig = px.line(
        agg_sorted,
        x="period",
        y="Demand",
        color="type_name",
        title=f"Electricity demand by fuel type ({start} to {end})",
        labels={"period": "Date", "Demand": ylabel, "type_name": "Fuel type"},
    )

fig.update_layout(
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# -------------------
# Plot Graph (Grid Stress & Demand Anomaly Detection)
# -------------------
st.subheader("Grid Stress & Demand Anomaly Detection")
st.markdown(
    f"Days where total demand deviates more than **{z_threshold}σ** from the mean are flagged."
)

daily = build_anomaly_data(df, ycol, z_threshold)

fig2 = go.Figure()
fig2.add_trace(
    go.Scatter(
        x=daily["period"],
        y=daily["total_demand"],
        mode="lines",
        name="Total demand",
        line=dict(color="#4C78A8", width=2),
    )
)

high_days = daily[daily["anomaly_type"] == "high"]
low_days = daily[daily["anomaly_type"] == "low"]

if not high_days.empty:
    fig2.add_trace(
        go.Scatter(
            x=high_days["period"],
            y=high_days["total_demand"],
            mode="markers",
            name="High-demand anomaly",
            marker=dict(color="red", size=10, symbol="triangle-up"),
            hovertemplate="<b>HIGH</b><br>%{x}<br>Demand: %{y:,.0f}<br>Z: %{customdata:.2f}",
            customdata=high_days["demand_zscore"],
        )
    )

if not low_days.empty:
    fig2.add_trace(
        go.Scatter(
            x=low_days["period"],
            y=low_days["total_demand"],
            mode="markers",
            name="Low-demand anomaly",
            marker=dict(color="blue", size=10, symbol="triangle-down"),
            hovertemplate="<b>LOW</b><br>%{x}<br>Demand: %{y:,.0f}<br>Z: %{customdata:.2f}",
            customdata=low_days["demand_zscore"],
        )
    )

fig2.update_layout(
    title="Total daily demand with anomaly markers",
    xaxis_title="Date",
    yaxis_title=ylabel,
    hovermode="x unified",
)
st.plotly_chart(fig2, use_container_width=True)

fig3 = px.bar(
    daily,
    x="period",
    y="demand_pct_change",
    title="Day-over-day % change in total demand",
    labels={"period": "Date", "demand_pct_change": "Change (%)"},
    color="demand_pct_change",
    color_continuous_scale=["blue", "lightgrey", "red"],
    color_continuous_midpoint=0,
)
fig3.update_layout(coloraxis_showscale=False)
st.plotly_chart(fig3, use_container_width=True)

n_high = (daily["anomaly_type"] == "high").sum()
n_low = (daily["anomaly_type"] == "low").sum()
col1, col2, col3 = st.columns(3)
col1.metric("Total days analyzed", len(daily))
col2.metric("High-demand anomaly days", n_high)
col3.metric("Low-demand anomaly days", n_low)

if not daily[daily["anomaly_type"].notna()].empty:
    with st.expander("View anomaly day details"):
        anomaly_table = daily[daily["anomaly_type"].notna()][
            [
                "period",
                "total_demand",
                "demand_zscore",
                "demand_pct_change",
                "anomaly_type",
            ]
        ].copy()
        anomaly_table["period"] = anomaly_table["period"].dt.strftime("%Y-%m-%d")
        anomaly_table.columns = ["Date", ylabel, "Z-Score", "Day-over-Day %", "Type"]
        st.dataframe(anomaly_table.reset_index(drop=True), use_container_width=True)

st.subheader("Fuel Mix Shifts on Anomaly Days")
st.markdown(
    "How does the **fuel mix (% share)** change on high- or low-demand days vs normal days?"
)

mix_comparison, shifts = build_mix_comparison(df, daily, ycol, anomaly_focus)

if mix_comparison.empty:
    st.info(
        "No anomaly days found with current threshold. Try lowering the z-score slider."
    )
else:
    label = "High" if anomaly_focus == "high_demand" else "Low"
    fig4 = px.bar(
        mix_comparison,
        x="type_name",
        y="avg_share_pct",
        color="day_type",
        barmode="group",
        title=f"Avg fuel share (%) — {label}-demand days vs normal",
        labels={
            "type_name": "Fuel type",
            "avg_share_pct": "Avg share (%)",
            "day_type": "Day type",
        },
        color_discrete_map={
            "high_demand": "#d62728",
            "low_demand": "#1f77b4",
            "normal": "#aec7e8",
        },
    )
    fig4.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig4, use_container_width=True)

    if not shifts.empty and "shift_pct" in shifts.columns:
        fig5 = px.bar(
            shifts,
            x="type_name",
            y="shift_pct",
            title=f"Fuel mix shift: {label}-demand days minus normal (percentage points)",
            labels={"type_name": "Fuel type", "shift_pct": "Shift (pp)"},
            color="shift_pct",
            color_continuous_scale=["blue", "lightgrey", "red"],
            color_continuous_midpoint=0,
        )
        fig5.update_layout(coloraxis_showscale=False, xaxis_tickangle=-35)
        st.plotly_chart(fig5, use_container_width=True)

        with st.expander("View shift data table"):
            st.dataframe(shifts.reset_index(drop=True), use_container_width=True)

elapsed = time.time() - start_time
st.caption(f"Page loaded in {elapsed:.2f} seconds")
