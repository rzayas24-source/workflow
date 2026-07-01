import streamlit as st
from db import get_conn
from site_util_attachments import get_first_pending

st.title("Site Itemization")

# ---------------------------------------------------------
# Determine which import_id we are itemizing
# ---------------------------------------------------------
if "current_attachment" not in st.session_state:
    st.session_state.current_attachment = get_first_pending()

attachment = st.session_state.current_attachment

if not attachment:
    st.info("No active import to itemize.")
    st.stop()

import_id = attachment["id"]

st.markdown(f"### Itemization for Import **{import_id}**")

# ---------------------------------------------------------
# Input fields (same as Tkinter version)
# ---------------------------------------------------------
fields = {
    "PostingDate": st.text_input("Posting Date"),
    "Type": st.text_input("Type"),
    "Amount": st.text_input("Amount"),
    "Payer": st.text_input("Payer"),
    "CheckNumber": st.text_input("Check Number"),
    "EDI": st.text_input("EDI"),
    "Poster": st.text_input("Poster"),
    "EOB": st.text_input("EOB"),
    "UnPosted": st.text_input("UnPosted"),
    "Misc": st.text_input("Misc"),
    "MiscType": st.text_input("Misc Type"),
    "Notes": st.text_input("Notes"),
    "Nick": st.text_input("Nick"),
    "Raul": st.text_input("Raul"),
    "Needs": st.text_input("Needs"),
    "FromAcct": st.text_input("From Account"),
    "ToAcct": st.text_input("To Account"),
}

# ---------------------------------------------------------
# Add row button
# ---------------------------------------------------------
if st.button("Add Row to Queue"):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO BalsheetSiteEntry
        (import_id, PostingDate, Type, Amount, Payer, CheckNumber, EDI, Poster,
         EOB, UnPosted, Misc, MiscType, Notes, Nick, Raul, Needs, FromAcct, ToAcct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        import_id,
        fields["PostingDate"],
        fields["Type"],
        fields["Amount"],
        fields["Payer"],
        fields["CheckNumber"],
        fields["EDI"],
        fields["Poster"],
        fields["EOB"],
        fields["UnPosted"],
        fields["Misc"],
        fields["MiscType"],
        fields["Notes"],
        fields["Nick"],
        fields["Raul"],
        fields["Needs"],
        fields["FromAcct"],
        fields["ToAcct"]
    ))

    conn.commit()
    conn.close()

    st.success("Row added to queue.")

# ---------------------------------------------------------
# View queued rows
# ---------------------------------------------------------
st.divider()
st.markdown("### Queued Rows")

conn = get_conn()
cur = conn.cursor()

cur.execute("""
    SELECT id, PostingDate, Type, Amount, Payer, CheckNumber
    FROM BalsheetSiteEntry
    WHERE import_id=?
""", (import_id,))

rows = cur.fetchall()
conn.close()

if rows:
    st.dataframe(rows)
else:
    st.info("No queued rows yet.")

# ---------------------------------------------------------
# Release button
# ---------------------------------------------------------
if st.button("Release to Balsheet"):
    st.session_state.release_import_id = import_id
    st.switch_page("site_pages_4_release")
