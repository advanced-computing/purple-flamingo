import streamlit as st
import pandas as pd
import requests
import plotly.express as px

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


def fetch_all_pages(base_url: str, params: dict) -> list:
    all_rows = []
    offset = 0
    length = params.get("length", 5000)

    while True:
        params["offset"] = offset
        r = requests.get(base_url, params=params, timeout=60)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("response", {}).get("data", [])
        all_rows.extend(rows)
        if len(rows) < length:
            break
        offset += length

    return all_rows


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

# Ignoring Na values
df["period"] = pd.to_datetime(df["period"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

# Convert units
ycol = "value"
ylabel = "Demand (MWh)"
if units == "GWh":
    df["value_gwh"] = df["value"] / 1000.0
    ycol = "value_gwh"
    ylabel = "Demand (GWh)"

# Aggregation by date and fuel type
agg = (
    df.groupby(["period", "type-name"], as_index=False)[ycol]
    .sum()
    .rename(columns={ycol: "Demand"})
)

# Keep top N fuel types by total
top_fuels = agg.groupby("type-name")["Demand"].sum().nlargest(top_n).index
agg = agg[agg["type-name"].isin(top_fuels)].copy()

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
