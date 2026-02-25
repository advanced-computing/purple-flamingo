import streamlit as st
import pandas as pd
import plotly.express as px

from data_utils import convert_units, parse_period_and_value, top_n_by_total
from eia_api import fetch_all_pages

st.set_page_config(page_title="EIA Fuel Type Demand", layout="wide")
st.title("U.S. Electricity Demand by Fuel Type (Eastern Time)")

# API Key Retrieval
api_key = st.secrets.get("EIA_API_KEY", None)

# Predefine time and unit values
start = st.sidebar.text_input("Start date (YYYY-MM-DD)", value="2026-02-09")
end = st.sidebar.text_input("End date (YYYY-MM-DD)", value="2026-02-16")
units = st.sidebar.radio("Units", ["MWh", "GWh"], horizontal=True)

# Adding in filters for user to choose for display
top_n = st.sidebar.slider("Show top N fuel types (by total)", 1, 15, 10)
filter_eastern = st.sidebar.checkbox("Filter to Eastern timezone only", value=True)

BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-fuel-type-data/data/"

@st.cache_data(show_spinner=False)
def load_fuel_data(api_key: str, start: str, end: str) -> pd.DataFrame:
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

with st.spinner("Loading data..."):
    df = load_fuel_data(api_key, start, end)

if df.empty:
    st.warning("No data returned. Check dates/API key.")
    st.stop()

df = parse_period_and_value(df)
df, ycol, ylabel = convert_units(df, units)

# Aggregation by date and fuel type
agg = (
    df.groupby(["period", "type-name"], as_index=False)[ycol]
      .sum()
      .rename(columns={ycol: "Demand"})
) # type: ignore

# Keep top N fuel types by total
agg = top_n_by_total(agg, "type-name", "Demand", top_n=top_n)

# Plot Graph
fig = px.line(
    agg.sort_values("period"),
    x="period",
    y="Demand",
    color="type-name",
    title=f"Electricity demand by fuel type ({start} to {end})",
    labels={"period": "Date", "Demand": ylabel, "type-name": "Fuel type"},
)
st.plotly_chart(fig, use_container_width=True)
