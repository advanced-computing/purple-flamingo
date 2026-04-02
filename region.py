import time

import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go
from google.api_core.exceptions import GoogleAPIError

from bigquery_utils import get_bigquery_client, get_bigquery_config, read_region_data
from data_utils import (
    convert_units,
    compute_daily_totals,
    demand_day_over_day_change,
    detect_demand_anomalies,
    drop_invalid_required_rows,
    parse_period_and_value,
    top_n_by_total,
)

start_time = time.time()

st.set_page_config(page_title="EIA Demand by Region (ET)", layout="wide")
st.title("U.S. Electricity Demand by Region")
st.caption("Data: U.S. Energy Information Administration (EIA), served from BigQuery")
st.markdown("**Team:** Aileen Yang · Aria Kovalovich · Chengpu Deng")

# Predefine Sidebar
with st.sidebar:
    st.header("Settings")

    start = st.text_input("Start date (YYYY-MM-DD)", value="2026-01-15")
    end = st.text_input("End date (YYYY-MM-DD)", value="2026-03-09")
    units = st.radio("Units", ["MWh", "GWh"], horizontal=True)
    top_n = st.slider("Show top N regions (by total)", 1, 20, 10)
    chart_type = st.radio("Chart type", ["Line", "Stacked Area"], index=0)

    st.divider()
    st.subheader("Anomaly Detection")
    z_threshold = st.slider(
        "Z-score threshold",
        min_value=0.5,
        max_value=3.0,
        value=1.5,
        step=0.1,
    )


@st.cache_resource(show_spinner=False)
def get_cached_bigquery_client():
    return get_bigquery_client(st.secrets)


@st.cache_data(show_spinner=False)
def load_region_data(start: str, end: str) -> pd.DataFrame:
    client = get_cached_bigquery_client()
    config = get_bigquery_config(st.secrets)
    raw_df = read_region_data(
        client=client,
        project_id=config["project_id"],
        dataset_id=config["dataset_id"],
        table_id=config["region_table_id"],
        start=start,
        end=end,
    )
    parsed_df = parse_period_and_value(raw_df)
    cleaned_df, _ = drop_invalid_required_rows(
        parsed_df, required_columns=["period", "value", "respondent"]
    )
    return cleaned_df


try:
    with st.spinner("Loading data from BigQuery..."):
        df = load_region_data(start, end)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
except GoogleAPIError as exc:
    st.error(f"BigQuery request failed: {exc}")
    st.stop()

if df.empty:
    st.warning("No rows returned from BigQuery for the selected date range.")
    st.stop()

df, parsed_warnings = drop_invalid_required_rows(
    df, required_columns=["period", "value", "respondent"]
)
for warning in parsed_warnings:
    st.warning(warning)

if df.empty:
    st.warning("No usable rows after cleaning and filtering.")
    st.stop()

df, ycol, ylabel = convert_units(df, units)

# ---------------------------
# Section 1: Regional demand chart
# ---------------------------
st.subheader("Electricity Demand by Region")

df_top = top_n_by_total(df, "respondent", ycol, top_n=top_n)
df_sorted = df_top.sort_values("period")

if chart_type == "Stacked Area":
    fig = px.area(
        df_sorted,
        x="period",
        y=ycol,
        color="respondent",
        title=f"U.S. electricity demand by region — stacked area ({start} to {end}), Eastern Time",
        labels={"period": "Date", ycol: ylabel, "respondent": "Region"},
    )
    fig.update_traces(mode="lines")
else:
    fig = px.line(
        df_sorted,
        x="period",
        y=ycol,
        color="respondent",
        title=f"U.S. electricity demand by region ({start} to {end}), Eastern Time",
        labels={"period": "Date", ycol: ylabel, "respondent": "Region"},
    )

fig.update_layout(
    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.01),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Section 2: Regional anomaly detection
# ---------------------------
st.subheader("Regional Demand Anomalies")

regions = sorted(df["respondent"].dropna().unique().tolist())
selected_region = st.selectbox(
    "Select a region to analyze for anomalies",
    options=regions,
    index=0,
)

df_region = df[df["respondent"] == selected_region].copy()
if df_region.empty:
    st.info(f"No data for region: {selected_region}")
else:
    daily = compute_daily_totals(df_region, value_col=ycol)
    daily = demand_day_over_day_change(daily)
    daily = detect_demand_anomalies(daily, z_threshold=z_threshold)

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
                name="High anomaly",
                marker=dict(color="red", size=10, symbol="triangle-up"),
            )
        )
    if not low_days.empty:
        fig2.add_trace(
            go.Scatter(
                x=low_days["period"],
                y=low_days["total_demand"],
                mode="markers",
                name="Low anomaly",
                marker=dict(color="blue", size=10, symbol="triangle-down"),
            )
        )

    fig2.update_layout(
        title=f"Total demand with anomalies — {selected_region}",
        xaxis_title="Date",
        yaxis_title=ylabel,
        hovermode="x unified",
    )
    st.plotly_chart(fig2, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Days analyzed", len(daily))
    col2.metric("High anomaly days", (daily["anomaly_type"] == "high").sum())
    col3.metric("Low anomaly days", (daily["anomaly_type"] == "low").sum())

    # Day-over-day change
    fig3 = px.bar(
        daily,
        x="period",
        y="demand_pct_change",
        title=f"Day-over-day % change — {selected_region}",
        labels={"period": "Date", "demand_pct_change": "Change (%)"},
        color="demand_pct_change",
        color_continuous_scale=["blue", "lightgrey", "red"],
        color_continuous_midpoint=0,
    )
    fig3.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------
# Section 3: Cross-region comparison on a selected date
# ---------------------------
st.subheader("Cross-Region Demand Snapshot")

available_dates = sorted(df["period"].dt.strftime("%Y-%m-%d").unique().tolist())
if available_dates:
    selected_date = st.selectbox(
        "Select a date to compare all regions",
        options=available_dates,
        index=len(available_dates) // 2,
    )
    day_df = df[df["period"].dt.strftime("%Y-%m-%d") == selected_date]
    day_agg = (
        day_df.groupby("respondent")[ycol]
        .sum()
        .reset_index()
        .sort_values(ycol, ascending=True)
    )

    fig4 = px.bar(
        day_agg,
        x=ycol,
        y="respondent",
        orientation="h",
        title=f"Total electricity demand by region on {selected_date}",
        labels={ycol: ylabel, "respondent": "Region"},
    )
    st.plotly_chart(fig4, use_container_width=True)

elapsed = time.time() - start_time
st.caption(f"Page loaded in {elapsed:.2f} seconds")
