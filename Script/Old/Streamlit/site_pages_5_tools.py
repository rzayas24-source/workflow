import streamlit as st
from db import get_conn

st.title("Site Tools & Admin Utilities")

st.markdown("### Administrative Tools")

# ---------------------------------------------------------
# Reset ALL Pending items back to Pending
# ---------------------------------------------------------
def reset_all_to_pending():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE imported_files
        SET review_status='Pending'
    """)
    conn.commit()
    conn.close()

if st.button("Reset ALL review_status to Pending"):
    reset_all_to_pending()
    st.success("All items reset to Pending.")


# ---------------------------------------------------------
# Reset ONLY NothingToPost → Pending
# ---------------------------------------------------------
def reset_nothing_to_post():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE imported_files
        SET review_status='Pending'
        WHERE review_status='NothingToPost'
    """)
    conn.commit()
    conn.close()

if st.button("Reset NothingToPost → Pending"):
    reset_nothing_to_post()
    st.success("NothingToPost items reset to Pending.")


# ---------------------------------------------------------
# Reset ONLY NotInBatch → Pending
# ---------------------------------------------------------
def reset_not_in_batch():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE imported_files
        SET review_status='Pending'
        WHERE review_status='NotInBatch'
    """)
    conn.commit()
    conn.close()

if st.button("Reset NotInBatch → Pending"):
    reset_not_in_batch()
    st.success("NotInBatch items reset to Pending.")


st.divider()
st.markdown("### Snapshot Utilities")

# ---------------------------------------------------------
# Trigger snapshot regeneration (folder-based)
# ---------------------------------------------------------
def regenerate_snapshots():
    # We call your existing script logic directly
    try:
        import site_snapshotgenerator
        site_snapshotgenerator.process_folder_pdfs()
        st.success("Snapshot regeneration complete.")
    except Exception as e:
        st.error(f"Snapshot regeneration failed: {e}")

if st.button("Regenerate Snapshots (Folder-Based)"):
    regenerate_snapshots()


st.divider()
st.markdown("### Email Ingestion Utilities")

# ---------------------------------------------------------
# Trigger email downloader
# ---------------------------------------------------------
def run_email_downloader():
    try:
        import site_emaildownloader
        site_emaildownloader.download_emails()
        st.success("Email download complete.")
    except Exception as e:
        st.error(f"Email download failed: {e}")

if st.button("Run Email Downloader"):
    run_email_downloader()


st.divider()
st.markdown("### Database Diagnostics")

# ---------------------------------------------------------
# Count Pending items
# ---------------------------------------------------------
def count_pending():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM imported_files
        WHERE review_status='Pending'
    """)
    count = cur.fetchone()[0]
    conn.close()
    return count

pending_count = count_pending()
st.info(f"Pending items: **{pending_count}**")


# ---------------------------------------------------------
# Count staged rows
# ---------------------------------------------------------
def count_staged():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM BalsheetSiteEntry")
    count = cur.fetchone()[0]
    conn.close()
    return count

staged_count = count_staged()
st.info(f"Staged rows in BalsheetSiteEntry: **{staged_count}**")
