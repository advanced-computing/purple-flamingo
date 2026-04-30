import time
from datetime import date, timedelta

import streamlit as st
import pandas as pd
import plotly.express as px
from google.api_core.exceptions import GoogleAPIError

from bigquery_utils import get_bigquery_client, get_bigquery_config, read_fuel_data
from data_utils import (
    convert_units,
    drop_invalid_required_rows,
    parse_period_and_value,
    top_n_by_total,
)

start_time = time.time()
default_end = date.today()
default_start = default_end - timedelta(days=90)

st.set_page_config(page_title="EIA Fuel Type Demand", layout="wide")
st.title("U.S. Electricity Demand by Fuel Type")
st.caption("Data: U.S. Energy Information Administration (EIA), served from BigQuery")
st.markdown("**Team:** Aileen Yang · Aria Kovalovich · Chengpu Deng")
st.info(
    "Use this page to see how electricity demand varies by fuel type over time. "
    "The line view is useful for comparing trends, while the stacked area view helps show "
    "how the overall generation mix changes."
)

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
def build_main_chart_data(df: pd.DataFrame, value_col: str, top_n: int) -> pd.DataFrame:
    chart_df = df.loc[:, ["period", "type_name", value_col]].rename(
        columns={value_col: "Demand"}
    )
    filtered = top_n_by_total(chart_df, "type_name", "Demand", top_n=top_n)
    return filtered.sort_values("period")


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
st.subheader("1. Electricity demand by fuel type")
st.caption("Compare demand across major fuel sources over the selected date range.")

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

elapsed = time.time() - start_time
st.caption(f"Page loaded in {elapsed:.2f} seconds")
