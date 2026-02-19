import streamlit as st

# Define the pages
main_page = st.Page("app.py", title="EIA Fuel Type Demand")
page_2 = st.Page("region.py", title="EIA Region Demand")

# Set up navigation
pg = st.navigation([main_page, page_2])

# Run the selected page
pg.run()