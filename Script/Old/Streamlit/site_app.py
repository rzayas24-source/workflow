import streamlit as st
import runpy

st.set_page_config(page_title="Site Review Workflow", layout="wide")

# ---------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------
page = st.sidebar.radio(
    "Navigation",
    [
        "Review",
        "Itemization",
        "Queue Viewer",
        "Release",
        "Tools"
    ]
)

# ---------------------------------------------------------
# Map sidebar selection → script filename
# ---------------------------------------------------------
page_map = {
    "Review": "site_pages_1_review.py",
    "Itemization": "site_pages_2_itemization.py",
    "Queue Viewer": "site_pages_3_queueviewer.py",
    "Release": "site_pages_4_release.py",
    "Tools": "site_pages_5_tools.py",
}

selected_script = page_map[page]

# ---------------------------------------------------------
# Clear caches so UI updates properly
# ---------------------------------------------------------
st.cache_data.clear()
st.cache_resource.clear()

# ---------------------------------------------------------
# Execute the selected page
# ---------------------------------------------------------
runpy.run_path(selected_script)
