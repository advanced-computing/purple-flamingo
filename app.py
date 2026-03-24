import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from data_utils import (
    compute_daily_totals,
    convert_units,
    demand_day_over_day_change,
    detect_demand_anomalies,
    filter_to_timezone,
    fuel_mix_on_anomaly_days,
    largest_fuel_shifts,
    parse_period_and_value,
    top_n_by_total,
)
from eia_api import fetch_daily_fuel
from schemas import validate_fuel_raw, validate_parsed

st.set_page_config(page_title="EIA Fuel Type Demand", layout="wide")
st.title("U.S. Electricity Demand by Fuel Type")
st.caption("Data: U.S. Energy Information Administration (EIA) — Eastern Time")
st.markdown("**Team:** Aileen Yang · Aria Kovalovich · Chengpu Deng")

# -------------------
# API Key Retrieval
# -------------------
api_key = st.secrets.get("EIA_API_KEY", None)
# BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-fuel-type-data/data/"
if not api_key:
    st.error("Missing EIA_API_KEY in Streamlit secrets.")
    st.stop()

# -------------------
# Sidebar Control
# -------------------
with st.sidebar:
    st.header("Settings")

    start = st.text_input("Start date (YYYY-MM-DD)", value="2026-01-15")
    end = st.text_input("End date (YYYY-MM-DD)", value="2026-03-08")
    units = st.radio("Units", ["MWh", "GWh"], horizontal=True)
    top_n = st.slider("Show top N fuel types (by total)", 1, 15, 10)
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
def load_fuel_data(api_key: str, start: str, end: str) -> pd.DataFrame:
    rows = fetch_daily_fuel(api_key, start, end)
    return pd.json_normalize(rows)


with st.spinner("Loading data from EIA..."):
    df_raw = load_fuel_data(api_key, start, end)

if df_raw.empty:
    st.warning("No data returned. Check API key.")
    st.stop()

df, raw_warnings = validate_fuel_raw(df_raw)
for warning in raw_warnings:
    st.warning(warning)

if df.empty:
    st.warning("No usable rows after raw data validation.")
    st.stop()

df = parse_period_and_value(df)
df, parsed_warnings = validate_parsed(
    df, required_columns=["period", "value", "type_name"]
)
for warning in parsed_warnings:
    st.warning(warning)

if filter_eastern:
    df = filter_to_timezone(df, "eastern")

if df.empty:
    st.warning("No usable rows after cleaning and filtering.")
    st.stop()

df, ycol, ylabel = convert_units(df, units)

# -------------------
# Aggregation by date and fuel type
# -------------------
agg = (
    df.groupby(["period", "type_name"], as_index=False)[ycol]
    .sum()
    .rename(columns={ycol: "Demand"})
)

# Keep top N fuel types by total
agg = top_n_by_total(agg, "type_name", "Demand", top_n=top_n)

# -------------------
# Plot Graph (Main Demand)
# -------------------
st.subheader("Electricity Demand by Fuel Type")
agg_sorted = agg.sort_values("period")

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

daily = compute_daily_totals(df, value_col=ycol)
daily = demand_day_over_day_change(daily)
daily = detect_demand_anomalies(daily, z_threshold=z_threshold)

# Plot total demand with anomaly markers
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

# Day-over-day change chart
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

# Summary table
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

# -------------------
# Plot Graph (Fuel Mix Shift on Anomaly Days)
# -------------------
st.subheader("Fuel Mix Shifts on Anomaly Days")
st.markdown(
    "How does the **fuel mix (% share)** change on high- or low-demand days vs normal days?"
)

# Re-use df with original value col for shares
mix_comparison = fuel_mix_on_anomaly_days(
    df,
    daily,
    fuel_col="type_name",
    value_col=ycol,
    anomaly_type="high" if anomaly_focus == "high_demand" else "low",
)

if mix_comparison.empty:
    st.info(
        "No anomaly days found with current threshold. Try lowering the z-score slider."
    )
else:
    shifts = largest_fuel_shifts(
        mix_comparison,
        fuel_col="type_name",
        anomaly_label="high_demand" if anomaly_focus == "high_demand" else "low_demand",
    )

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
