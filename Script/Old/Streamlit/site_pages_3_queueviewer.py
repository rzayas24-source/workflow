import streamlit as st
from db import get_conn
from site_util_attachments import get_first_pending

st.title("Site Queue Viewer")

# ---------------------------------------------------------
# Determine active import_id
# ---------------------------------------------------------
if "current_attachment" not in st.session_state:
    st.session_state.current_attachment = get_first_pending()

attachment = st.session_state.current_attachment

if not attachment:
    st.info("No active import to view.")
    st.stop()

import_id = attachment["id"]

st.markdown(f"### Queued Rows for Import **{import_id}**")

# ---------------------------------------------------------
# Load queued rows
# ---------------------------------------------------------
def load_rows():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, PostingDate, Type, Amount, Payer, CheckNumber,
               EDI, Poster, EOB, UnPosted, Misc, MiscType,
               Notes, Nick, Raul, Needs, FromAcct, ToAcct
        FROM BalsheetSiteEntry
        WHERE import_id=?
    """, (import_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

rows = load_rows()

# ---------------------------------------------------------
# Display rows
# ---------------------------------------------------------
if rows:
    st.dataframe(rows)
else:
    st.info("No queued rows for this import.")

# ---------------------------------------------------------
# Refresh button
# ---------------------------------------------------------
if st.button("Refresh Queue"):
    st.experimental_rerun()

# ---------------------------------------------------------
# Approve button (same behavior as Tkinter)
# ---------------------------------------------------------
if st.button("Approve Queue"):
    st.success("Rows approved. You may now Release to Balsheet.")

# ---------------------------------------------------------
# Release navigation
# ---------------------------------------------------------
if st.button("Go to Release Page"):
    st.session_state.release_import_id = import_id
    st.switch_page("site_pages_4_release")
