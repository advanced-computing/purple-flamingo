import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import (
    convert_units,
    filter_to_timezone,
    parse_period_and_value,
    top_n_by_total,
)
from eia_api import fetch_all_pages
from schemas import validate_parsed, validate_region_raw

st.set_page_config(page_title="EIA Demand by Region (ET)", layout="wide")
st.title("U.S. Electricity Demand by Region (Eastern Time)")

# API Key Retrieval
api_key = st.secrets.get("EIA_API_KEY", None)

# Predefine time and unit values
start = st.sidebar.text_input("Start date (YYYY-MM-DD)", value="2026-02-09")
end = st.sidebar.text_input("End date (YYYY-MM-DD)", value="2026-02-16")
units = st.sidebar.radio("Units", ["MWh", "GWh"], horizontal=True)

BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"


@st.cache_data(show_spinner=False)
def load_region_data(api_key: str, start: str, end: str) -> pd.DataFrame:
    params = {
        "api_key": api_key,
        "frequency": "daily",
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "offset": 0,
        "length": 5000,
    }
    rows = fetch_all_pages(BASE_URL, params)
    return pd.json_normalize(rows)


with st.spinner("Loading data from EIA..."):
    df = load_region_data(api_key, start, end)

if df.empty:
    st.warning("No data returned. Double-check your dates and API key.")
    st.stop()

df, raw_warnings = validate_region_raw(df)
for warning in raw_warnings:
    st.warning(warning)

if df.empty:
    st.warning("No usable rows after raw data validation.")
    st.stop()

df = parse_period_and_value(df)
df, parsed_warnings = validate_parsed(df, required_columns=["period", "value", "respondent"])
for warning in parsed_warnings:
    st.warning(warning)

# Fix to Eastern Time
df = filter_to_timezone(df, "eastern")

if df.empty:
    st.warning("No usable rows after cleaning and filtering.")
    st.stop()

df, ycol, ylabel = convert_units(df, units)

# Plot Graph
df = top_n_by_total(df, "respondent", "value", top_n=10)
region_col = "respondent"

fig = px.line(
    df.sort_values("period"),
    x="period",
    y=ycol,
    color=region_col,
    title=f"U.S. electricity demand by region ({start} to {end}), Eastern Time",
    labels={"period": "Date", ycol: ylabel, region_col: "Region"},
)
st.plotly_chart(fig, use_container_width=True)
