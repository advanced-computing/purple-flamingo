import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from plotly.subplots import make_subplots

from bigquery_utils import (
    get_bigquery_client,
    get_bigquery_config,
    read_pricing_data,
    read_region_data,
)

start_time = time.time()

ISO_TO_RESPONDENT = {"CAISO": "CISO", "NYISO": "NYIS", "ERCOT": "ERCO"}
RESPONDENT_TO_ISO = {v: k for k, v in ISO_TO_RESPONDENT.items()}
ALL_ISOS = list(ISO_TO_RESPONDENT.keys())
ISO_COLORS = {"CAISO": "#e07b39", "NYISO": "#54a24b", "ERCOT": "#4C78A8"}

default_end = date.today()
default_start = default_end - timedelta(days=90)

st.set_page_config(page_title="Price–Demand Analysis", layout="wide")
st.title("Electricity Price–Demand Analysis by ISO")
st.caption(
    "Hourly LMP prices from gridstatus (CAISO · NYISO · ERCOT) "
    "matched with EIA daily region demand, served from BigQuery"
)
st.markdown("**Team:** Aileen Yang · Aria Kovalovich · Chengpu Deng")
st.info(
    "Use this page to compare wholesale electricity prices with electricity demand. "
    "Prices come from GridStatus, while demand comes from EIA regional demand data."
)

with st.sidebar:
    st.header("Controls")

    st.subheader("Date range")
    start = st.text_input("Start date (YYYY-MM-DD)", value=default_start.isoformat())
    end = st.text_input("End date (YYYY-MM-DD)", value=default_end.isoformat())

    st.divider()
    st.subheader("Display options")
    selected_isos = st.multiselect(
        "ISOs to display",
        options=ALL_ISOS,
        default=ALL_ISOS,
    )
    lmp_agg = st.radio(
        "Wholesale price aggregation across locations",
        ["Mean", "Median"],
        horizontal=True,
    )

if not selected_isos:
    st.warning("Select at least one ISO in the sidebar.")
    st.stop()


@st.cache_resource(show_spinner=False)
def get_cached_bigquery_client():
    return get_bigquery_client(st.secrets)


@st.cache_data(show_spinner=False)
def load_price_data(start: str, end: str) -> pd.DataFrame:
    client = get_cached_bigquery_client()
    config = get_bigquery_config(st.secrets)
    df = read_pricing_data(
        client=client,
        project_id=config["project_id"],
        dataset_id=config["dataset_id"],
        table_id=config["pricing_table_id"],
        start=start,
        end=end,
    )
    df["period"] = pd.to_datetime(df["period"]).dt.date
    df["lmp"] = pd.to_numeric(df["lmp"], errors="coerce")
    df["energy"] = pd.to_numeric(df["energy"], errors="coerce")
    df["congestion"] = pd.to_numeric(df["congestion"], errors="coerce")
    df["loss"] = pd.to_numeric(df["loss"], errors="coerce")
    df["interval_start"] = pd.to_datetime(df["interval_start"], utc=True)
    return df.dropna(subset=["period", "lmp"])


@st.cache_data(show_spinner=False)
def load_demand_data(start: str, end: str) -> pd.DataFrame:
    client = get_cached_bigquery_client()
    config = get_bigquery_config(st.secrets)
    raw = read_region_data(
        client=client,
        project_id=config["project_id"],
        dataset_id=config["dataset_id"],
        table_id=config["region_table_id"],
        start=start,
        end=end,
    )
    raw["period"] = pd.to_datetime(raw["period"]).dt.date
    raw["value"] = pd.to_numeric(raw["value"], errors="coerce")
    raw = raw.dropna(subset=["period", "value", "respondent"])
    raw["iso"] = raw["respondent"].map(RESPONDENT_TO_ISO)
    return raw[raw["iso"].notna()].copy()


def aggregate_daily_prices(price_df: pd.DataFrame, agg: str) -> pd.DataFrame:
    fn = "mean" if agg == "Mean" else "median"
    return (
        price_df.groupby(["iso", "period"])
        .agg(
            avg_lmp=("lmp", fn),
            avg_energy=("energy", fn),
            avg_congestion=("congestion", fn),
            avg_loss=("loss", fn),
            max_lmp=("lmp", "max"),
            min_lmp=("lmp", "min"),
        )
        .reset_index()
    )


def aggregate_daily_demand(demand_df: pd.DataFrame) -> pd.DataFrame:
    return (
        demand_df.groupby(["iso", "period"])["value"]
        .sum()
        .reset_index()
        .rename(columns={"value": "total_demand_gwh"})
        .assign(total_demand_gwh=lambda d: d["total_demand_gwh"] / 1000)
    )


try:
    with st.spinner("Loading price and demand data from BigQuery..."):
        price_df = load_price_data(start, end)
        demand_df = load_demand_data(start, end)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
except GoogleAPIError as exc:
    st.error(f"BigQuery request failed: {exc}")
    st.stop()

if price_df.empty:
    st.warning("No price data returned for the selected date range.")
    st.stop()
if demand_df.empty:
    st.warning("No demand data returned for the selected date range.")
    st.stop()

price_df = price_df[price_df["iso"].isin(selected_isos)].copy()
demand_df = demand_df[demand_df["iso"].isin(selected_isos)].copy()

daily_prices = aggregate_daily_prices(price_df, lmp_agg)
daily_demand = aggregate_daily_demand(demand_df)
merged = pd.merge(daily_prices, daily_demand, on=["iso", "period"], how="inner")

if merged.empty:
    st.warning(
        "No overlapping price and demand data found. "
        "The price table covers CAISO/NYISO/ERCOT; "
        "the demand table uses EIA respondent codes CISO/NYIS/ERCO. "
        "Check that both tables are populated for the selected date range."
    )
    st.stop()

merged["period_dt"] = pd.to_datetime(merged["period"])
daily_prices["period_dt"] = pd.to_datetime(daily_prices["period"])

# ---------------------------
# Section 0: Summary metrics
# ---------------------------
st.divider()
st.subheader("1. Summary by ISO")
st.caption(
    "These cards summarize average wholesale prices, average daily demand, and the price-demand correlation."
)
cols = st.columns(len(selected_isos))
for col, iso in zip(cols, selected_isos):
    iso_df = merged[merged["iso"] == iso]
    if iso_df.empty:
        col.warning(f"{iso}: no merged data")
        continue
    valid = iso_df.dropna(subset=["avg_lmp", "total_demand_gwh"])
    r = (
        np.corrcoef(valid["avg_lmp"], valid["total_demand_gwh"])[0, 1]
        if len(valid) >= 2
        else float("nan")
    )
    col.metric(
        f"{iso} — average wholesale price", f"${iso_df['avg_lmp'].mean():.2f} /MWh"
    )
    col.metric("Avg daily demand", f"{iso_df['total_demand_gwh'].mean():,.0f} GWh")
    col.metric(
        "Price-demand correlation",
        f"{r:.3f}" if not np.isnan(r) else "N/A",
        help="Pearson correlation between daily average wholesale price and total daily demand",
    )

# ---------------------------
# Section 1: Dual-axis time series
# ---------------------------
st.divider()
st.subheader("2. Wholesale price and demand over time")
st.caption(
    "Solid line = wholesale price on the left axis. Blue dashed line = demand on the right axis."
)

n = len(selected_isos)
fig1 = make_subplots(
    rows=n,
    cols=1,
    subplot_titles=selected_isos,
    specs=[[{"secondary_y": True}]] * n,
    vertical_spacing=0.14,
    shared_xaxes=True,
)
fig1.update_layout(height=300 * n, hovermode="x unified")

for i, iso in enumerate(selected_isos, start=1):
    iso_df = merged[merged["iso"] == iso].sort_values("period_dt")
    color = ISO_COLORS.get(iso, "#888")
    fig1.add_trace(
        go.Scatter(
            x=iso_df["period_dt"],
            y=iso_df["avg_lmp"],
            name="Average wholesale price ($/MWh)",
            mode="lines+markers",
            line=dict(color=color, width=2),
            legendgroup="lmp",
            showlegend=(i == 1),
        ),
        row=i,
        col=1,
        secondary_y=False,
    )
    fig1.add_trace(
        go.Scatter(
            x=iso_df["period_dt"],
            y=iso_df["total_demand_gwh"],
            name="Total demand (GWh)",
            mode="lines+markers",
            line=dict(color="#4C78A8", width=2, dash="dot"),
            legendgroup="demand",
            showlegend=(i == 1),
        ),
        row=i,
        col=1,
        secondary_y=True,
    )
    fig1.update_yaxes(
        title_text="Wholesale price ($/MWh)", secondary_y=False, row=i, col=1
    )
    fig1.update_yaxes(title_text="Demand (GWh)", secondary_y=True, row=i, col=1)

fig1.update_xaxes(title_text="Date", row=n, col=1)
fig1.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig1, use_container_width=True)

# ---------------------------
# Section 2: Price vs demand scatter
# ---------------------------
st.divider()
st.subheader("3. Price-demand relationship")
st.caption(
    f"Each point = one day ({start} to {end}). "
    "Dashed line = linear trend. "
    "With only 7 days, treat slopes as directional rather than statistically robust."
)

fig2 = go.Figure()
for iso in selected_isos:
    iso_df = merged[merged["iso"] == iso].dropna(subset=["avg_lmp", "total_demand_gwh"])
    if iso_df.empty:
        continue
    color = ISO_COLORS.get(iso, "#888")
    x = iso_df["avg_lmp"].values
    y = iso_df["total_demand_gwh"].values

    fig2.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="markers+text",
            name=iso,
            text=iso_df["period"].astype(str),
            textposition="top center",
            textfont=dict(size=9),
            marker=dict(color=color, size=11),
            hovertemplate=(
                f"<b>{iso}</b><br>Date: %{{text}}<br>"
                "Wholesale price: $%{x:.2f}/MWh<br>Demand: %{y:,.0f} GWh<extra></extra>"
            ),
        )
    )
    if len(x) >= 2:
        m, b = np.polyfit(x, y, 1)
        x_line = np.linspace(x.min(), x.max(), 50)
        fig2.add_trace(
            go.Scatter(
                x=x_line,
                y=m * x_line + b,
                mode="lines",
                line=dict(color=color, dash="dash", width=1),
                showlegend=False,
            )
        )

fig2.update_layout(
    xaxis_title="Daily average wholesale price ($/MWh)",
    yaxis_title="Total daily demand (GWh)",
    hovermode="closest",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig2, use_container_width=True)

# ---------------------------
# Section 3: Intraday LMP profile
# ---------------------------
st.divider()
st.subheader("4. Intraday wholesale price profile")
st.caption(
    "Average wholesale price by hour of day (UTC) across the selected period and all locations"
)

price_df["hour"] = price_df["interval_start"].dt.hour
hourly_agg = (
    price_df.groupby(["iso", "hour"])["lmp"]
    .mean()
    .reset_index()
    .rename(columns={"lmp": "avg_lmp"})
)

if not hourly_agg.empty:
    pivot = hourly_agg.pivot(index="iso", columns="hour", values="avg_lmp")
    fig3 = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="RdYlGn_r",
        title="Average wholesale price by hour of day ($/MWh)",
        labels={"x": "Hour of day (UTC)", "y": "ISO", "color": "Average price ($/MWh)"},
        text_auto=".1f",
    )
    fig3.update_xaxes(tickmode="linear", dtick=2)
    st.plotly_chart(fig3, use_container_width=True)

# ---------------------------
# Section 4: LMP component breakdown
# ---------------------------
st.divider()
st.subheader("5. Wholesale price component breakdown")
st.caption(
    "Average energy, congestion, and loss components of wholesale prices by ISO over the selected period"
)

comp_df = (
    daily_prices[daily_prices["iso"].isin(selected_isos)]
    .groupby("iso")[["avg_energy", "avg_congestion", "avg_loss"]]
    .mean()
    .reset_index()
    .melt(id_vars="iso", var_name="component", value_name="avg_value")
)
comp_df["component"] = (
    comp_df["component"].str.replace("avg_", "", regex=False).str.capitalize()
)

fig4 = px.bar(
    comp_df,
    x="iso",
    y="avg_value",
    color="component",
    barmode="stack",
    title="Average wholesale price components by ISO ($/MWh)",
    labels={"iso": "ISO", "avg_value": "$/MWh", "component": "Component"},
    color_discrete_map={
        "Energy": "#4C78A8",
        "Congestion": "#f28e2b",
        "Loss": "#59a14f",
    },
)
st.plotly_chart(fig4, use_container_width=True)

# ---------------------------
# Data table
# ---------------------------
with st.expander("View merged daily price and demand data"):
    display_df = merged[
        ["iso", "period", "avg_lmp", "max_lmp", "min_lmp", "total_demand_gwh"]
    ].copy()
    display_df.columns = [
        "ISO",
        "Date",
        "Average Wholesale Price ($/MWh)",
        "Maximum Wholesale Price ($/MWh)",
        "Minimum Wholesale Price ($/MWh)",
        "Total Demand (GWh)",
    ]
    st.dataframe(display_df.reset_index(drop=True), use_container_width=True)

elapsed = time.time() - start_time
st.caption(f"Page loaded in {elapsed:.2f} seconds")
