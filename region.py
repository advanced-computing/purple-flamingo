import streamlit as st
import pandas as pd
import requests
import plotly.express as px

st.set_page_config(page_title="EIA Demand by Region (ET)", layout="wide")
st.title("U.S. Electricity Demand by Region (Eastern Time)")

# API Key Retrieval
api_key = st.secrets.get("EIA_API_KEY", None)

# Predefine time and unit values
start = st.sidebar.text_input("Start date (YYYY-MM-DD)", value="2026-02-09")
end = st.sidebar.text_input("End date (YYYY-MM-DD)", value="2026-02-16")
units = st.sidebar.radio("Units", ["MWh", "GWh"], horizontal=True)

BASE_URL = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"


def fetch_all_pages(base_url: str, params: dict) -> list:
    # Pagination
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
    df = pd.json_normalize(rows)
    return df


with st.spinner("Loading data from EIA..."):
    df = load_region_data(api_key, start, end)

if df.empty:
    st.warning("No data returned. Double-check your dates and API key.")
    st.stop()

df["period"] = pd.to_datetime(df["period"], errors="coerce")
df["value"] = pd.to_numeric(df["value"], errors="coerce")

# Fix to Eastern Time
if "timezone" in df.columns:
    df = df[df["timezone"].str.lower().eq("eastern")]

# Convert units if needed
ycol = "value"
ylabel = "Demand (MWh)"
if units == "GWh":
    df["value_gwh"] = df["value"] / 1000.0
    ycol = "value_gwh"
    ylabel = "Demand (GWh)"

# Choose region label
region_col = (
    "region-name"
    if "region-name" in df.columns
    else ("region" if "region" in df.columns else None)
)

# Plot Graph
top10 = df.groupby("respondent")["value"].sum().nlargest(10).index
df = df[df["respondent"].isin(top10)].copy()
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
