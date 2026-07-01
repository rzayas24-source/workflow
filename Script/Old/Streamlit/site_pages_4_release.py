import streamlit as st
from db import get_conn

st.title("Site Release to Balsheet")

# ---------------------------------------------------------
# Determine import_id to release
# ---------------------------------------------------------
if "release_import_id" not in st.session_state:
    st.error("No import selected for release.")
    st.stop()

import_id = st.session_state.release_import_id

st.markdown(f"### Ready to release Import **{import_id}** to Balsheet")

# ---------------------------------------------------------
# Preview queued rows before release
# ---------------------------------------------------------
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

if rows:
    st.dataframe(rows)
else:
    st.info("No queued rows found for this import.")

st.divider()

# ---------------------------------------------------------
# Release logic (same as Tkinter)
# ---------------------------------------------------------
def release_to_balsheet():
    conn = get_conn()
    cur = conn.cursor()

    # Move rows into Balsheet
    cur.execute("""
        INSERT INTO Balsheet
        (PostingDate, Type, Amount, Payer, CheckNumber, EDI, Poster,
         EOB, UnPosted, Misc, MiscType, Notes, Nick, Raul, Needs,
         FromAcct, ToAcct)
        SELECT PostingDate, Type, Amount, Payer, CheckNumber, EDI, Poster,
               EOB, UnPosted, Misc, MiscType, Notes, Nick, Raul, Needs,
               FromAcct, ToAcct
        FROM BalsheetSiteEntry
        WHERE import_id=?
    """, (import_id,))

    # Clear staging
    cur.execute("""
        DELETE FROM BalsheetSiteEntry
        WHERE import_id=?
    """, (import_id,))

    # Mark imported_files as posted
    cur.execute("""
        UPDATE imported_files
        SET review_status='PostedToBalsheet'
        WHERE id=?
    """, (import_id,))

    conn.commit()
    conn.close()

# ---------------------------------------------------------
# Release button
# ---------------------------------------------------------
if st.button("Release Now"):
    release_to_balsheet()
    st.success(f"Import {import_id} released to Balsheet.")
    st.toast("Release complete.")
