"""
EDI LOADER MODULE — NORMALIZED VERSION
-------------------------------------
This version:

 - Accepts all .txt files
 - Parses converted TRN-style structure
 - Normalizes all dates to MM/DD/YYYY
 - Stores filename in the EDI table
 - Prevents duplicate check_numbers
 - Lists duplicate check_numbers clearly
 - Only moves file if at least one new row is inserted
 - Prints full diagnostics
 - Verifies all dates at the end
 - Pauses at the end
"""

import os
import shutil
from datetime import datetime
from db import get_conn  # ⭐ dynamic DB connection

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

TRN_FOLDER = r"C:\Renfrew\2.AVATAR\3_TRN_Bulk_Check"
ARCHIVE_FOLDER = r"C:\Renfrew\2.AVATAR\3_TRN_Bulk_Check\Loaded"

# ---------------------------------------------------------
# STARTUP
# ---------------------------------------------------------

print(">>> EDI Loader script started")
print(f">>> Using TRN folder: {TRN_FOLDER}")
print(f">>> Using Archive folder: {ARCHIVE_FOLDER}")
print("--------------------------------------------------")

# ---------------------------------------------------------
# DB SETUP
# ---------------------------------------------------------

def init_edi_table():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS EDI (
            id INTEGER PRIMARY KEY,
            check_date TEXT,
            check_number TEXT,
            check_amount REAL,
            filename TEXT
        );
    """)
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# DATE NORMALIZATION
# ---------------------------------------------------------

def normalize_mmddyyyy(s):
    if not s:
        return None

    s = str(s).strip()

    if "/" in s and len(s) == 10:
        return s

    if len(s) == 8 and s.isdigit():
        yyyy = s[0:4]
        mm = s[4:6]
        dd = s[6:8]
        return f"{mm}/{dd}/{yyyy}"

    fmts = ["%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%y"]
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.strftime("%m/%d/%Y")
        except:
            pass

    return s

# ---------------------------------------------------------
# FILE PARSER
# ---------------------------------------------------------

def parse_trn_file(path):
    rows = []

    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if len(lines) < 3:
        print(f"  WARNING: File {os.path.basename(path)} has fewer than 3 lines")
        return rows

    data_lines = lines[2:]

    for line in data_lines:
        parts = line.split()
        if len(parts) < 3:
            print(f"  WARNING: Skipping malformed line: {line}")
            continue

        raw_date = parts[0]
        check_date = normalize_mmddyyyy(raw_date)
        check_number = parts[1]
        check_amount = parts[2]

        try:
            amount = float(check_amount)
        except:
            print(f"  WARNING: Invalid amount '{check_amount}' in file {path}")
            continue

        rows.append((check_date, check_number, amount))

    return rows

# ---------------------------------------------------------
# DATE VERIFICATION
# ---------------------------------------------------------

def verify_edi_dates():
    conn = get_conn()
    bad_rows = conn.execute("""
        SELECT id, check_date, check_number
        FROM EDI
        WHERE check_date NOT LIKE '__/__/____'
           OR LENGTH(check_date) != 10
    """).fetchall()
    conn.close()

    print("\n>>> DATE VERIFICATION REPORT (EDI)")
    print("--------------------------------------------------")

    if not bad_rows:
        print("All EDI dates are correctly normalized to MM/DD/YYYY.")
        return

    print("WARNING: Some EDI rows have NON-normalized dates:")
    for r in bad_rows:
        print(f"  ID {r['id']}: {r['check_date']}  (Check#: {r['check_number']})")

    print("\nYou should correct these rows or re-import the affected files.")

# ---------------------------------------------------------
# LOADER WITH DUPLICATE PROTECTION + CONDITIONAL ARCHIVING
# ---------------------------------------------------------

def load_all_trn_files():
    print("\n>>> Checking TRN folder...")

    if not os.path.exists(TRN_FOLDER):
        print(">>> ERROR: TRN folder does NOT exist!")
        print(TRN_FOLDER)
        input("Press ENTER to exit...")
        return

    print(">>> TRN folder exists.")

    print("\n>>> Initializing EDI table...")
    init_edi_table()

    conn = get_conn()
    cur = conn.cursor()

    print("\n>>> Scanning folder for TXT files...")
    print("--------------------------------------------------")

    file_count = 0
    txt_count = 0
    row_count = 0

    for filename in os.listdir(TRN_FOLDER):
        file_count += 1
        print(f"Found file: {filename}")

        if not filename.lower().endswith(".txt"):
            print("  Skipped (not .txt)")
            continue

        txt_count += 1
        full_path = os.path.join(TRN_FOLDER, filename)

        print(f"  Processing: {filename}")
        rows = parse_trn_file(full_path)
        print(f"  Parsed rows: {len(rows)}")

        new_rows = []
        duplicate_rows = []

        for r in rows:
            check_date, check_number, amount = r

            exists = cur.execute("""
                SELECT 1 FROM EDI
                WHERE check_number = ?
            """, (check_number,)).fetchone()

            if exists:
                duplicate_rows.append(check_number)
            else:
                new_rows.append(r)

        if len(new_rows) == 0:
            print(f"\n  >>> FILE REJECTED — NO NEW ROWS FOUND: {filename}")
            print("  >>> DUPLICATE CHECK NUMBERS IN THIS FILE:")
            for dup in duplicate_rows:
                print(f"      - {dup}")
            print("  >>> FILE NOT MOVED. PLEASE REVIEW.\n")
            print("--------------------------------------------------")
            continue

        print(f"  >>> FILE ACCEPTED — {len(new_rows)} NEW ROWS FOUND.")

        if duplicate_rows:
            print("  >>> DUPLICATES FOUND (these were skipped):")
            for dup in duplicate_rows:
                print(f"      - {dup}")

        for r in new_rows:
            check_date, check_number, amount = r

            cur.execute("""
                INSERT INTO EDI (check_date, check_number, check_amount, filename)
                VALUES (?, ?, ?, ?)
            """, (check_date, check_number, amount, filename))

            print(f"    INSERTED: {check_date} {check_number} {amount} {filename}")
            row_count += 1

        archive_path = os.path.join(ARCHIVE_FOLDER, filename)
        try:
            shutil.move(full_path, archive_path)
            print(f"  Moved to archive: {archive_path}")
        except Exception as e:
            print(f"  ERROR moving file to archive: {e}")

        print("--------------------------------------------------")

    conn.commit()

    print("\n>>> Gathering diagnostics...")

    total_rows = conn.execute("SELECT COUNT(*) AS c FROM EDI").fetchone()["c"]
    preview_first = conn.execute("SELECT * FROM EDI ORDER BY id ASC LIMIT 10").fetchall()
    preview_last = conn.execute("SELECT * FROM EDI ORDER BY id DESC LIMIT 10").fetchall()

    conn.close()

    print("\n==================== EDI LOAD DIAGNOSTICS ====================")
    print(f"Files scanned:           {file_count}")
    print(f"TXT files processed:     {txt_count}")
    print(f"Rows inserted this run:  {row_count}")
    print(f"Total rows in EDI table: {total_rows}")
    print("--------------------------------------------------------------")

    print("\nFIRST 10 ROWS:")
    for r in preview_first:
        print(f"{r['check_date']}   {r['check_number']}   {r['check_amount']}   {r['filename']}")

    print("\nLAST 10 ROWS:")
    for r in preview_last:
        print(f"{r['check_date']}   {r['check_number']}   {r['check_amount']}   {r['filename']}")

    print("\n==============================================================")

    verify_edi_dates()

    input("Press ENTER to exit...")

# ---------------------------------------------------------
# AUTO-RUN
# ---------------------------------------------------------

if __name__ == "__main__":
    load_all_trn_files()
