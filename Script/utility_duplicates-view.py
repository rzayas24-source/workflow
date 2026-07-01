#!/usr/bin/env python3

import sys
from datetime import datetime
from tabulate import tabulate   # <-- ADDED

sys.path.append(r"C:\Renfrew\Workflow")

from db import get_conn   # ⭐ unified DB engine

# ANSI Colors
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

print(">>> EDI / Lockbox / EFT Duplicate Filename Viewer (Bank Day)")
print("-------------------------------------------------------------")

# -------------------------------
# DATE NORMALIZER
# -------------------------------
def normalize_mmddyyyy(s):
    if not s:
        return ""
    s = str(s).strip().replace("-", "/")

    fmts = [
        "%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d",
        "%m/%d/%y", "%Y%m%d"
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f).strftime("%m/%d/%Y")
        except:
            pass

    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 8:
        for fmt in ("%Y%m%d", "%m%d%Y"):
            try:
                return datetime.strptime(digits, fmt).strftime("%m/%d/%Y")
            except:
                pass

    return s

# -------------------------------
# DB HELPERS
# -------------------------------
def get_current_workday():
    conn = get_conn()
    row = conn.execute("SELECT current_work_day FROM work_state WHERE id = 1").fetchone()
    conn.close()
    if row and row["current_work_day"]:
        return normalize_mmddyyyy(row["current_work_day"])
    return None

def get_bank_day_for_workday(workday):
    conn = get_conn()
    row = conn.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (workday,)
    ).fetchone()
    conn.close()
    return normalize_mmddyyyy(row["bank_day"]) if row else None

# -------------------------------
# GET CURRENT WORKDAY → BANK DAY
# -------------------------------
workday = get_current_workday()

if not workday:
    print("ERROR: No current work day is set.")
    input("\nPress ENTER to exit...")
    sys.exit()

bank_day = get_bank_day_for_workday(workday)

if not bank_day:
    print(f"ERROR: Could not map paperwork day {workday} to a bank day.")
    input("\nPress ENTER to exit...")
    sys.exit()

print(f"\nCurrent Workday (paperwork): {YELLOW}{workday}{RESET}")
print(f"Mapped Bank Day:             {CYAN}{bank_day}{RESET}\n")

# -------------------------------
# MAIN QUERY
# -------------------------------
conn = get_conn()

rows = conn.execute("""
SELECT
    e.filename AS filename,
    e.check_number AS edi_check,
    e.check_amount AS edi_amount,
    lb.[Transaction Total] AS lockbox_amount,
    eft.Amount AS eft_amount,
    COALESCE(eft.Date, lb.[Deposit Date]) AS match_date
FROM EDI e
LEFT JOIN Lockbox lb
    ON TRIM(e.check_number) = TRIM(lb.[Check Number])
LEFT JOIN EFT eft
    ON TRIM(e.check_number) = TRIM(eft.CheckNumber)
WHERE COALESCE(eft.Date, lb.[Deposit Date]) IS NOT NULL
ORDER BY e.filename, e.check_number;
""").fetchall()

conn.close()

# -------------------------------
# FILTER TO BANK DAY
# -------------------------------
filtered = []
for r in rows:
    dt = normalize_mmddyyyy(r["match_date"])
    if dt == bank_day:
        filtered.append(r)

# -------------------------------
# FIND DUPLICATE FILENAMES
# -------------------------------
filename_counts = {}
for r in filtered:
    fn = r["filename"]
    if fn:
        filename_counts[fn] = filename_counts.get(fn, 0) + 1

duplicate_filenames = {fn for fn, c in filename_counts.items() if c > 1}

if not duplicate_filenames:
    print(f"No duplicate filenames found for bank day {bank_day}.")
    input("\nPress ENTER to exit...")
    sys.exit()

print(f"{YELLOW}Duplicate filenames found:{RESET}")
for fn in duplicate_filenames:
    print(f" - {fn}")
print()

# -------------------------------
# BUILD TABULATE TABLE
# -------------------------------
table_data = []

for r in filtered:
    if r["filename"] not in duplicate_filenames:
        continue

    # Format amounts
    try:
        lb = f"{float(r['lockbox_amount']):,.2f}" if r['lockbox_amount'] else ""
    except:
        lb = r['lockbox_amount'] or ""

    try:
        eft = f"{float(r['eft_amount']):,.2f}" if r['eft_amount'] else ""
    except:
        eft = r['eft_amount'] or ""

    dt = normalize_mmddyyyy(r["match_date"])

    table_data.append([
        r["filename"],
        r["edi_check"],
        lb,
        eft,
        dt
    ])

# -------------------------------
# DISPLAY TABLE USING TABULATE
# -------------------------------
headers = ["Filename", "EDI Check", "Lockbox", "EFT", "Date"]

print(tabulate(table_data, headers=headers, tablefmt="grid"))
print()

print(f">>> Duplicate filename rows shown: {len(table_data)}")
print(">>> Complete.")

input("Press ENTER to exit...")
