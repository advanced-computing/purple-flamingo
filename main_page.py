import streamlit as st

# Define the pages
main_page = st.Page("app.py", title="EIA Fuel Type Demand")
page_2 = st.Page("region.py", title="EIA Region Demand")
page_3 = st.Page("grid_stress.py", title="Grid Stress & Anomaly Analysis")
page_4 = st.Page("price_demand.py", title="Price–Demand Analysis")
page_5 = st.Page("proposal.py", title="Project Proposal, Feedback, and Reflections")
# Set up navigation
pg = st.navigation([main_page, page_2, page_3, page_4, page_5])

# Run the selected page
pg.run()
