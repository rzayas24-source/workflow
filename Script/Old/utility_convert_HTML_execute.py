#!/usr/bin/env python3

import os
from db import get_conn

# ⭐ UPDATED FOLDER — HTML EOB DIRECTORY
HTML_EOB_FOLDER = r"C:\Renfrew\2.AVATAR\1_HTML-EOB"


def file_contains_check(full_path, chk):
    """Strict matching logic used in the converter."""
    try:
        with open(full_path, "r", errors="ignore") as file:
            contents = file.read()

            if chk in contents:
                return True
            if f"TRN*1*{chk}" in contents:
                return True
            if "BPR*" in contents and chk in contents:
                return True

            return False
    except:
        return False


def execute_html_renames():
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    # Load queued rename operations
    rows = cur.execute("""
        SELECT check_number, proposed_name
        FROM proposed_edi
        ORDER BY created_at
    """).fetchall()

    html_files = os.listdir(HTML_EOB_FOLDER)

    print("\n==============================")
    print(" EXECUTING HTML EOB FILE RENAMES")
    print("==============================\n")

    # ⭐ Diagnostics counters
    total = 0
    renamed = 0
    skipped_existing = 0
    skipped_no_match = 0
    skipped_no_proposed = 0
    errors = 0

    for r in rows:
        total += 1
        chk = r["check_number"]
        new_name = r["proposed_name"]

        # Skip if proposed name is missing
        if not new_name:
            print(f"Check {chk}: No proposed name — SKIPPED")
            skipped_no_proposed += 1
            continue

        # Skip if file already exists (safety)
        new_path = os.path.join(HTML_EOB_FOLDER, new_name)
        if os.path.exists(new_path):
            print(f"Check {chk}: {new_name} already exists — SKIPPED")
            skipped_existing += 1
            continue

        # Find the HTML file containing the check
        old_file = None
        for f in html_files:
            full_path = os.path.join(HTML_EOB_FOLDER, f)
            if file_contains_check(full_path, chk):
                old_file = f
                break

        if not old_file:
            print(f"Check {chk}: No matching HTML EOB file found — SKIPPED")
            skipped_no_match += 1
            continue

        old_path = os.path.join(HTML_EOB_FOLDER, old_file)

        # Attempt rename
        try:
            os.rename(old_path, new_path)
            print(f"Renamed: {old_file} → {new_name}")

            renamed += 1

            # Optional: log rename
            cur.execute("""
                INSERT INTO rename_log (check_number, old_name, new_name)
                VALUES (?, ?, ?)
            """, (chk, old_file, new_name))

        except Exception as e:
            print(f"Rename failed for {old_file}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    # ⭐ FINAL DIAGNOSTICS
    print("\n==============================")
    print(" HTML EOB RENAME — DIAGNOSTICS")
    print("==============================\n")
    print(f"Total queued items:          {total}")
    print(f"Successfully renamed:        {renamed}")
    print(f"Skipped (existing file):     {skipped_existing}")
    print(f"Skipped (no match found):    {skipped_no_match}")
    print(f"Skipped (no proposed name):  {skipped_no_proposed}")
    print(f"Errors during rename:        {errors}")
    print("==============================\n")

    input("Press ENTER to exit...")


if __name__ == "__main__":
    execute_html_renames()
