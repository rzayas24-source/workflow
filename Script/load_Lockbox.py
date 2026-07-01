#!/usr/bin/env python3

from db import get_conn
import os
import shutil
import pandas as pd

DOWNLOADS = r"\\ren-fs01\users\rzayas\Downloads"
ARCHIVE = r"C:\Renfrew\Workflow\Archive"

def find_lockbox_file():
    for f in os.listdir(DOWNLOADS):
        if f.startswith("SearchResults") and f.lower().endswith(".xls"):
            return os.path.join(DOWNLOADS, f)
    return None

def main():
    # ---------------------------------------------------------
    # 1. FIND FILE
    # ---------------------------------------------------------
    file_path = find_lockbox_file()

    if not file_path:
        print("\n❌ No SearchResults*.xls file found in Downloads.")
        input("\nPress ENTER to exit...")
        return

    print(f"\nFound file: {file_path}")

    # ---------------------------------------------------------
    # 2. CONNECT TO DATABASE
    # ---------------------------------------------------------
    conn = get_conn()
    cur = conn.cursor()

    # ---------------------------------------------------------
    # 3. LOAD EXCEL INTO STAGING (LockboxLoad)
    # ---------------------------------------------------------
    print("\nLoading Excel into LockboxLoad...")

    df = pd.read_excel(file_path, dtype=str).fillna("")

    cur.execute("DELETE FROM LockboxLoad;")
    df.to_sql("LockboxLoad", conn, if_exists="append", index=False)

    cur.execute("SELECT COUNT(*) FROM LockboxLoad;")
    staging_count = cur.fetchone()[0]

    print(f"Rows loaded into staging: {staging_count}")

    if staging_count == 0:
        print("\n❌ ERROR: Staging is empty. Nothing to load.")
        conn.close()
        input("\nPress ENTER to exit...")
        return

    # ---------------------------------------------------------
    # 4. DUPLICATE PREVENTION
    # ---------------------------------------------------------
    print("\nChecking for duplicate Check Numbers...")

    cur.execute("""
        SELECT DISTINCT L."Check Number"
        FROM LockboxLoad L
        INNER JOIN Lockbox F
        ON L."Check Number" = F."Check Number"
        WHERE L."Check Number" IS NOT NULL AND L."Check Number" != '';
    """)

    duplicates = cur.fetchall()

    if duplicates:
        print("\n❌ DUPLICATE DETECTED — Load rejected.")
        print("These Check Numbers already exist in Lockbox:\n")

        for d in duplicates:
            print(f" - {d[0]}")

        print("\nStaging NOT loaded. File NOT archived.")
        print("Please correct the file and try again.")

        print("\n=== DIAGNOSTICS ===")
        print(f"Staging rows: {staging_count}")
        cur.execute("SELECT COUNT(*) FROM Lockbox;")
        print(f"Lockbox rows: {cur.fetchone()[0]}")
        print("Status: DUPLICATE FAILURE")

        conn.close()
        input("\nPress ENTER to exit...")
        return

    print("No duplicates found. Safe to load.")

    # ---------------------------------------------------------
    # 5. LOAD STAGING INTO FINAL TABLE
    # ---------------------------------------------------------
    print("\nLoading data into Lockbox...")

    cur.execute("""
        INSERT INTO Lockbox (
            "Transaction Number", "Status", "Note", "Transaction Total",
            "Deposit Date", "Batch Number", "Check Number", "Check Amount",
            "Site", "Lockbox", "Payor", "Sequence", "Number of Items"
        )
        SELECT
            "Transaction Number", "Status", "Note", "Transaction Total",
            "Deposit Date", "Batch Number", "Check Number", "Check Amount",
            "Site", "Lockbox", "Payor", "Sequence", "Number of Items"
        FROM LockboxLoad;
    """)

    inserted = cur.rowcount
    print(f"Rows inserted into Lockbox: {inserted}")

    # ---------------------------------------------------------
    # 6. CLEAR STAGING
    # ---------------------------------------------------------
    cur.execute("DELETE FROM LockboxLoad;")
    print("Staging cleared.")

    conn.commit()

    # ---------------------------------------------------------
    # 7. ARCHIVE FILE
    # ---------------------------------------------------------
    archive_path = os.path.join(ARCHIVE, os.path.basename(file_path))
    shutil.move(file_path, archive_path)

    print(f"\nFile archived to: {archive_path}")

    # ---------------------------------------------------------
    # 8. FINAL DIAGNOSTICS
    # ---------------------------------------------------------
    print("\n=== FINAL DIAGNOSTICS ===")

    print(f"Inserted rows: {inserted}")

    cur.execute("SELECT COUNT(*) FROM Lockbox;")
    print(f"Lockbox total rows: {cur.fetchone()[0]}")

    cur.execute("SELECT COUNT(*) FROM LockboxLoad;")
    print(f"LockboxLoad rows (after clear): {cur.fetchone()[0]}")

    print("Status: SUCCESS")

    conn.close()
    input("\nPress ENTER to exit...")

if __name__ == "__main__":
    main()
