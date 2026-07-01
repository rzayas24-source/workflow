import streamlit as st
import os
from PIL import Image
from db import get_conn
from site_util_attachments import get_first_pending, get_attachment_by_offset
import pandas as pd

# ---------------------------------------------------------
# Copilot Wave Banner — "The Renfrew Center"
# ---------------------------------------------------------
st.markdown("""
<style>
#custom-banner {
    background: linear-gradient(135deg, #0057ff 0%, #7a00ff 50%, #8a4dfc 100%);
    color: white;
    padding: 1.4rem 1.6rem;
    font-size: 1.55rem;
    font-weight: 700;
    border-radius: 14px;
    margin-bottom: 2rem;
    background-size: 200% 200%;
    animation: waveMove 6s ease infinite;
    box-shadow: 0 4px 14px rgba(0,0,0,0.18);
    letter-spacing: 0.7px;
    font-family: 'Segoe UI', sans-serif;
}

@keyframes waveMove {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
</style>

<div id="custom-banner">The Renfrew Center</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CSS — Copilot Red LEFT Pane + Safe Padding + Skinny Buttons
# ---------------------------------------------------------
st.markdown("""
<style>

/* SAFE TOP PADDING */
main, .block-container {
    padding-top: 4.5rem !important;
    margin-top: 0rem !important;
}

/* LEFT PANE COPILOT RED */
div[data-testid="column"]:first-child {
    background-color: #ff3366 !important;
    padding: 1rem !important;
    border-radius: 12px;
}

/* LEFT PANE TEXT COLOR */
div[data-testid="column"]:first-child * {
    color: white !important;
}

/* Skinny nav buttons */
button[kind="secondary"], button[kind="primary"] {
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
    font-size: 0.80rem !important;
}

/* Right pane fun styling */
div[data-testid="column"]:last-child {
    background-color: #f5f7fa !important;
    padding: 1rem !important;
    border-radius: 12px;
}

/* Expander headers */
.st-expanderHeader {
    font-weight: 600 !important;
    font-size: 1rem !important;
}

/* Sticky subtotal bar */
#subtotal-bar {
    position: sticky;
    bottom: 0;
    background-color: #ffe6ee;
    padding: 0.4rem;
    border-top: 1px solid #ff99bb;
    z-index: 999;
    color: #1a1a1a;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Initialize session state
# ---------------------------------------------------------
if "current_attachment" not in st.session_state:
    st.session_state.current_attachment = get_first_pending()

if "payment_fields" not in st.session_state:
    st.session_state.payment_fields = {
        "Site": "",
        "Check": "0.00",
        "Cash": "0.00",
        "Credit Card": "0.00",
        "Wire Transfer": "0.00",
        "Foreign Check": "0.00",
        "EFT": "0.00",
        "Lockbox": "0.00",
        "Misc": "0.00",
        "MiscType": "",
    }

attachment = st.session_state.current_attachment

# ---------------------------------------------------------
# Layout
# ---------------------------------------------------------
left, right = st.columns([7, 3])

# ---------------------------------------------------------
# LEFT PANE — Copilot Red Theme + Skinny Navigation Buttons
# ---------------------------------------------------------
with left:
    st.markdown(f"**{attachment['filename']}**")

    snapshot_path = attachment["snapshot_path"]

    if snapshot_path and os.path.exists(snapshot_path):
        st.image(snapshot_path, width=600)
    else:
        st.warning("Snapshot file not found.")

    nav_prev, nav_next = st.columns([1, 1])

    with nav_prev:
        if st.button("⬅ Prev", key="nav_prev"):
            prev = get_attachment_by_offset(attachment["id"], "prev")
            if prev:
                st.session_state.current_attachment = prev
                st.experimental_rerun()

    with nav_next:
        if st.button("Next ➡", key="nav_next"):
            nxt = get_attachment_by_offset(attachment["id"], "next")
            if nxt:
                st.session_state.current_attachment = nxt
                st.experimental_rerun()

# ---------------------------------------------------------
# RIGHT PANE — Fun Theme + Spreadsheet Entry
# ---------------------------------------------------------
with right:

    # -----------------------------------------------------
    # NAVIGATION SECTION (expanded)
    # -----------------------------------------------------
    with st.expander("Navigation", expanded=True):

        nav1, nav2 = st.columns([1, 1])

        with nav1:
            if st.button("⬅ Prev (Right Pane)", key="right_prev"):
                prev = get_attachment_by_offset(attachment["id"], "prev")
                if prev:
                    st.session_state.current_attachment = prev
                    st.experimental_rerun()

        with nav2:
            if st.button("Next ➡ (Right Pane)", key="right_next"):
                nxt = get_attachment_by_offset(attachment["id"], "next")
                if nxt:
                    st.session_state.current_attachment = nxt
                    st.experimental_rerun()

    # -----------------------------------------------------
    # Helper: Spreadsheet-style entry
    # -----------------------------------------------------
    def spreadsheet_section(title, fields):
        with st.expander(title, expanded=False):
            df = pd.DataFrame({
                "Field": fields,
                "Amount": [st.session_state.payment_fields[f] for f in fields]
            })

            edited = st.data_editor(
                df,
                hide_index=True,
                num_rows="fixed",
                column_config={
                    "Field": st.column_config.TextColumn(disabled=True),
                    "Amount": st.column_config.NumberColumn(format="%.2f")
                }
            )

            for i, row in edited.iterrows():
                st.session_state.payment_fields[row["Field"]] = f"{float(row['Amount']):.2f}"

    # -----------------------------------------------------
    # SITE SECTION
    # -----------------------------------------------------
    with st.expander("Site", expanded=False):
        st.session_state.payment_fields["Site"] = st.text_input(
            "Site",
            value=st.session_state.payment_fields["Site"],
            key="site_field"
        )

    # -----------------------------------------------------
    # PAYMENT SECTION (spreadsheet)
    # -----------------------------------------------------
    spreadsheet_section("Payment", ["Check", "Cash", "Credit Card"])

    # -----------------------------------------------------
    # BANK SECTION (spreadsheet)
    # -----------------------------------------------------
    spreadsheet_section("Bank", ["Lockbox", "EFT"])

    # -----------------------------------------------------
    # OTHER SECTION (spreadsheet)
    # -----------------------------------------------------
    spreadsheet_section("Other", ["Wire Transfer", "Foreign Check"])

    # -----------------------------------------------------
    # MISC SECTION (spreadsheet + detail)
    # -----------------------------------------------------
    with st.expander("Misc", expanded=False):
        spreadsheet_section("Misc Amounts", ["Misc"])
        st.session_state.payment_fields["MiscType"] = st.text_input(
            "Misc Detail",
            value=st.session_state.payment_fields["MiscType"],
            key="pay_MiscType"
        )

    # -----------------------------------------------------
    # BATCH DETAIL SECTION
    # -----------------------------------------------------
    with st.expander("Batch Detail", expanded=False):

        def update_status(new_status):
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                UPDATE imported_files
                SET review_status=?
                WHERE id=?
            """, (new_status, attachment["id"]))
            conn.commit()
            conn.close()
            st.toast(f"Marked as {new_status}")

        b1, b2 = st.columns([1, 1])

        with b1:
            if st.button("Nothing In Batch"):
                update_status("NothingToPost")

        with b2:
            if st.button("Not Part Of Batch"):
                update_status("NotInBatch")

    # -----------------------------------------------------
    # Subtotal (sticky bar)
    # -----------------------------------------------------
    total = sum([
        float(st.session_state.payment_fields["Check"]),
        float(st.session_state.payment_fields["Cash"]),
        float(st.session_state.payment_fields["Credit Card"]),
        float(st.session_state.payment_fields["Wire Transfer"]),
        float(st.session_state.payment_fields["Foreign Check"]),
        float(st.session_state.payment_fields["EFT"]),
        float(st.session_state.payment_fields["Lockbox"]),
        float(st.session_state.payment_fields["Misc"]),
    ])

    st.markdown(f"""
    <div id="subtotal-bar">
        <b>Subtotal: ${total:,.2f}</b>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.write("Itemization and Tools are available in the sidebar.")
