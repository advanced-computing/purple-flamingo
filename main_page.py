import streamlit as st

# Define the pages
main_page = st.Page("app.py", title="EIA Fuel Type Demand")
page_2 = st.Page("region.py", title="EIA Region Demand")
page_3 = st.Page("proposal.py", title="Project Proposal, Feedback, and Reflections")
# Set up navigation
pg = st.navigation([main_page, page_2, page_3])

# Run the selected page
pg.run()
