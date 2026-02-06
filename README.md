1. What dataset are you going to use?

   EIA Hourly Electric Grid Monitor

    Source: U.S. Energy Information Administration (EIA)

    1. API - Electric Power Operations (Daily and Hourly) https://www.eia.gov/opendata/browser/electricity/rto

    2. API documentation: https://www.eia.gov/opendata/documentation.php

    Frequency: Hourly, updated daily

    Coverage: Balancing Authorities and Regional Transmission Organizations across the U.S.

    Key variables:

    1. Electricity demand (load)

    2. Net generation

    3. Generation by fuel type (coal, gas, nuclear, wind, solar, etc.)

    4. Interchange (imports/exports)

   Optional second dataset to integrate if time and capacity allow: NOAA National Weather Service Hourly Weather Data
    1. Source: NOAA Integrated Surface Database (ISD) or NOAA API
    2. Frequency: Hourly (updated daily)
    3. Variables:
       1. Temperature
       2. Precipitation (rain/snow)
       3. Snow depth
       4. Wind speed
       5. Severe weather indicators

2. What are your research question(s)?
   Phase 1 Research Questions (Using Just EIA Data):
     1. How does the electricity generation mix change during periods of unusually high or low demand?
        1. During demand spikes, which fuel types increase the most across regions?
     2. Are periods of elevated grid stress—measured by sharp demand changes from weather events, infrastructure failure, etc.—observable in the EIA data?
     3. Can we identify anomalous hours or days where regions rely more heavily on imports or rapid generation shifts?

   Phase 2 Research Questions (if team time and capacity allow):
   If time and technical capacity permit, we will extend the analysis by incorporating NOAA weather data:
     1. How are temperature extremes associated with changes in electricity demand across regions?
        1. Do regions exhibit different demand sensitivity to heat and cold?
     2. Do adverse weather conditions (e.g., extreme heat, cold, precipitation, snow) coincide with observable changes in the electricity generation mix or interregional power flows?
        1. For example, is there increased reliance on natural gas or imports during cold snaps?
     3. How does grid behavior before, during, and after major weather events compare to typical conditions?
        1. Using weather events as reference points, how quickly does the grid respond and recover?

3. What's the link to your notebook?

https://github.com/advanced-computing/purple-flamingo/pull/1

4. What's your target visualization?

Here’s a recent graph showing a sharp increase in coal usage in New England during Winter Storm Fern just over a week ago, using the EIA hourly grid monitor, sourced from the “Energy Bad Boys” substack:

<img width="1339" height="664" alt="Screenshot 2026-02-06 at 14 14 42" src="https://github.com/user-attachments/assets/c1417ac8-6e5d-41e1-aa7e-edbef41235d6" />

5. What are your known unknowns?

   1. Which recent adverse grid or events will be cleanest and most interesting to analyze?
   2. Which ISO/RTO(s) will be most interesting to focus on that have consistent, standard data?
   3. If we pursue Phase 2, how cleanly can NOAA weather stations be matched to EIA balancing authorities?
   4. Whether fuel type and grid load variables are reported consistently?
   5. Whether weather variables (e.g. temperature, precipitation, snow) variables are consistently reported in a standardized way across weather stations?

6. What challenges do you anticipate?
   1. Managing High-Frequency, High-Volume Time Series Data: Given the data volume of both datasets we are contemplating, we will need to:
      1. spend time narrowing down the project scope to specific region(s) and event(s).
      2. hourly data across one or more regions will require efficient ingestion that runs on a schedule and avoids duplicates, storage, and querying data efficiently for interactive dashboards
      3. Understanding data quality - is there missing data for hours or regions? Are there reporting anomalies?
      4. Learning how the API works, handling any rate limits
      5. How are we defining grid stress? Adverse weather conditions?
 
   2. If we do Phase 2, geospatial mapping and data integration:
      1. EIA data is reported by balancing authority while NOAA data is station-based; we might need to aggregate weather stations into regions that match RTO or balancing authority
      2. Picking extreme weather event type, instance, definition
      3. Data cleaning: missing observations, inconsistencies in reporting across regions
      4. Time-series data combination complexity: upsampling/downsampling might be needed to get a clean match

