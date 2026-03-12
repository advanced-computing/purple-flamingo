import streamlit as st

st.set_page_config(page_title="Project Proposal & Reflection", layout="wide")

st.title("Project Proposal, Feedback, and Reflections")

st.markdown(
"""
This page documents the evolution of our project proposal, including reflections
after initial implementation and feedback from the teaching team.
"""
)

st.divider()

# ---------------------------------------------------
# REFLECTIONS AND TWEAKS (TOP SECTION)
# ---------------------------------------------------

st.header("Reflections and Project Adjustments")

st.subheader("How the Project Scope Evolved")
st.markdown("""
Our original proposal outlined a fairly ambitious project that aimed to simultaneously analyze electricity demand, fuel mix changes, interregional grid behavior, and weather impacts across multiple U.S. regions using high-frequency EIA data and NOAA weather data. In retrospect, Sneha's feedback correctly identified that this scope was too broad for the timeline of the assignment and the complexity of the datasets involved.
In response, we significantly narrowed the scope of the project. Rather than attempting to integrate multiple datasets and compare behavior across many regions and weather events, we focused the project on a single analytical question using only the EIA Electricity Grid Monitor data: how electricity demand and generation by fuel type behave during unusually high or low demand periods.
This adjustment allowed us to shift from a very broad universe of potetial research questions to a more focused and implementable analytical framework. Instead of attempting to build a large multi-region comparative system or honing in on one or more specific extreme weather events, we concentrated on developing a pipeline that could reliably ingest EIA data, clean and validate it, aggregate demand by fuel type, and identify anomalous periods of electricity demand.
By narrowing the scope in this way, we were more confident that with the skills and in the time we have, we could produce a functioning analytical dashboard that clearly visualizes demand patterns, detects demand anomalies, and explores how the electricity generation mix changes during these periods.
""")

st.subheader("Defining and Detecting Grid Stress")
st.markdown("""
Another key point of Sneha's feedback concerned how we intended to define and detect “periods of elevated grid stress.” When we wrote the original proposal, we had not yet decided how to define and operationalize this.
As part of refining the project methodology, we implemented a statistical, data-driven definition of grid stress based on demand anomalies, rather than picking a theoretical or scientific definition from academic literature. Specifically, we compute total daily electricity demand and identify periods where demand deviates from the mean by a configurable number of standard deviations (a z-score threshold). Days with unusually high demand are classified as high-demand anomalies, while unusually low demand days are classified as low-demand anomalies.
This approach simplfies the analysis and makes it reproducible and adjustable, since the anomaly threshold can be modified interactively in the dashboard.
Once anomalous demand periods are detected, the application compares the fuel mix shares on those days to normal demand days in order to explore how generation composition shifts during periods of unusually high or low load.
""")

st.subheader("Methodological Learning")
st.markdown("""
Through the implementation process we gained experience in several methodological areas:
Working with APIs and automated data ingestion.
We learned how to query the EIA API, normalize the returned JSON data into structured tables, and handle potential issues such as missing fields or inconsistent formats.

Data validation and cleaning.
Because API responses can contain missing or malformed records, we implemented validation functions that check required columns, ensure timestamps are properly parsed, and filter out unusable rows before analysis.

Time-series aggregation and transformation.
Although the original dataset is high-frequency, meaningful visualization required aggregating data across time and grouping it by fuel type. This required careful handling of timestamps and consistent units.

Designing interpretable anomaly detection.
Translating an abstract idea like “grid stress” into a measurable indicator required selecting a clear statistical rule and implementing it in a way that users can understand and interact with.
""")

st.subheader("Decisions About Weather Data Integration")
st.markdown("""
The original proposal included a second phase involving integration of NOAA weather data. After beginning exploratory work, we have decided thus far not to implement this component.
While weather data are highly relevant to electricity demand patterns, matching weather station observations to EIA balancing authorities introduces several additional layers of complexity, including spatial aggregation, inconsistent station reporting, and potential differences in time resolution. Given the time constraints of the assignment, incorporating this dataset would have significantly expanded the scope of the project.
Instead, we prioritized building a simple yet stable analysis we felt confident in using the EIA dataset alone. However, either weather integration or a case study analyzing a particular extreme event, remains two directions we can take future work, for example for analyzing demand spikes associated with a recent heat waves or winter storm.
""")

st.divider()

# ---------------------------------------------------
# TA FEEDBACK (MIDDLE SECTION)
# ---------------------------------------------------

st.header("Teaching Assistant Feedback")

st.subheader("Sneha's Feedback and Suggestions")
st.markdown("""
Hi team, thanks for your proposal! Good start; here are a few important concerns to resolve:

The project scope is currently very large. You’re mixing multiple dimensions at once: multi-region comparison, high-frequency time series, fuel mix analysis, weather integration, etc. You should narrow this significantly. 
For example, you might focus on peak demand behavior in one ISO/RTO, or analyze a single class of weather events (e.g., winter storms or heat waves), rather than trying to cover all extremes everywhere.
You can also decide whether you are studying general demand patterns or specific case-study events. A well-defined event-driven analysis (e.g., one winter storm) can be analytically rich rather than a broad exploratory dashboard across all regions and times.
Also, can you clarify how you are measuring or planning to look at “periods of elevated grid stress"?
Are you defining stress based on demand spikes, external event lists, or some threshold rule? 
Would be helpful to dive a bit more deeply into how those periods will be detected, as well as what data source or metric makes them observable.
The notebook currently doesn't have any code in it. Please update! It needs to demonstrate working code that actually loads and inspects the data from the EIA API.
Please also verify early that the NOAA data is accessible, clean, and usable at the resolution you want. Weather datasets often look straightforward in documentation but can be messy in practice (inconsistent reporting, metadata issues, etc.). Before committing to Phase 2, try pulling a sample region and confirm that you can realistically match it to a balancing authority.
Let me know if you have any questions or concerns about the feedback! Remember that these proposals are not set in stone, so feel free to modify as necessary. And of course, my and Professor Feldman's OH are always open to discuss. Good luck!
""")

st.divider()

# ---------------------------------------------------
# ORIGINAL PROPOSAL (BOTTOM SECTION)
# ---------------------------------------------------

st.header("Original Project Proposal")

st.subheader("1) Dataset")

st.markdown("""
**EIA Hourly Electric Grid Monitor**

Source: U.S. Energy Information Administration (EIA)  
API - Electric Power Operations (Daily and Hourly)  
https://www.eia.gov/opendata/browser/electricity/rto  

API documentation:  
https://www.eia.gov/opendata/documentation.php  

Frequency: Hourly, updated daily  

Coverage: Balancing Authorities and Regional Transmission Organizations across the U.S.

Key variables:
- Electricity demand (load)
- Net generation
- Generation by fuel type (coal, gas, nuclear, wind, solar, etc.)
- Interchange (imports/exports)
""")

st.markdown("""
**Optional second dataset: NOAA Weather Data**

Source: NOAA Integrated Surface Database (ISD)

Variables:
- Temperature
- Precipitation
- Snow depth
- Wind speed
- Severe weather indicators
""")

st.subheader("2) Research Questions")

st.markdown("""
### Phase 1 Research Questions (EIA Data)

- How does the electricity generation mix change during periods of unusually high or low demand?
- During demand spikes, which fuel types increase the most across regions?
- Are periods of elevated grid stress observable in the EIA data?
- Can we identify anomalous hours or days where regions rely more heavily on imports or rapid generation shifts?

### Phase 2 Research Questions (if time permits)

- How are temperature extremes associated with changes in electricity demand across regions?
- Do regions exhibit different demand sensitivity to heat and cold?
- Do adverse weather conditions coincide with changes in the electricity generation mix or power flows?
- How quickly does the grid respond and recover from extreme weather events?
""")

st.subheader("3) Notebook Link")

st.markdown("""
https://github.com/advanced-computing/purple-flamingo/pull/1
""")

st.subheader("4) Target Visualization")

st.markdown("""
Example: Visualization of a spike in coal generation in New England during Winter Storm Fern,
using EIA hourly grid monitor data.
""")

st.subheader("5) Known Unknowns")

st.markdown("""
- Which grid events will be most interesting to analyze?
- Which ISO/RTO regions have the most reliable data?
- Whether NOAA weather stations can be cleanly matched to balancing authorities
- Whether fuel and load variables are consistently reported
- Whether weather variables are standardized across stations
""")

st.subheader("Anticipated Challenges")

st.markdown("""
**High-frequency time series data**
- Managing hourly data volumes
- Efficient ingestion and querying

**Data quality issues**
- Missing observations
- Reporting anomalies

**API limitations**
- Learning API structure
- Handling rate limits

**Definitions**
- Defining grid stress
- Defining adverse weather events

**Phase 2 integration**
- Matching NOAA weather stations with EIA regions
- Handling time-series alignment
- Geospatial aggregation
""")
