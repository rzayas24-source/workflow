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
ORANGE = "\033[38;5;208m"
RESET = "\033[0m"

print(">>> EDI Filename Match Viewer (Counts + Missing Items)")
print("------------------------------------------------------")

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

def fmt(v):
    if v is None or v == "":
        return ""
    try:
        return f"{float(v):,.2f}"
    except:
        return str(v)

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
# LOAD ALL MATCH RESULTS
# -------------------------------
conn = get_conn()

rows = conn.execute("""
SELECT 
    E.filename,
    M.edi_check,
    M.edi_amount,
    M.lockbox_amount,
    M.eft_amount,
    M.match_date
FROM EDI_MatchResults M
LEFT JOIN EDI E
    ON E.check_number = M.edi_check
ORDER BY M.match_date ASC, M.edi_check ASC
""").fetchall()

conn.close()

# -------------------------------
# COUNT TOTAL OCCURRENCES PER FILENAME (A)
# -------------------------------
countA = {}
for r in rows:
    fn = r["filename"]
    if fn:
        countA[fn] = countA.get(fn, 0) + 1

# -------------------------------
# FILTER ROWS TO CURRENT BANK DAY
# -------------------------------
today_rows = []
other_rows = []

for r in rows:
    dt = normalize_mmddyyyy(r["match_date"])
    if dt == bank_day:
        today_rows.append(r)
    else:
        other_rows.append(r)

# -------------------------------
# COUNT TODAY OCCURRENCES PER FILENAME (B)
# -------------------------------
countB = {}
for r in today_rows:
    fn = r["filename"]
    if fn:
        countB[fn] = countB.get(fn, 0) + 1

# -------------------------------
# TABULATE: TODAY'S ROWS
# -------------------------------
table_today = []

for r in today_rows:
    fn = r["filename"] or ""
    A = countA.get(fn, 1)
    B = countB.get(fn, 0)

    table_today.append([
        fn,
        r["edi_check"],
        fmt(r["edi_amount"]),
        fmt(r["lockbox_amount"]),
        fmt(r["eft_amount"]),
        normalize_mmddyyyy(r["match_date"]),
        f"{A} {B}"
    ])

print(tabulate(
    table_today,
    headers=["Filename", "Check#", "EDI Amt", "LB Amt", "EFT Amt", "Bank Date", "A B"],
    tablefmt="grid"
))

print(f"\nRows for bank day {bank_day}: {len(today_rows)}")

# -------------------------------
# FIND FILENAMES WHERE A > B
# -------------------------------
filenames_today = {r["filename"] for r in today_rows if r["filename"]}

filenames_with_missing = [
    fn for fn in filenames_today
    if countA.get(fn, 0) > countB.get(fn, 0)
]

if not filenames_with_missing:
    print(f"\n{GREEN}No missing items. All files match expected counts.{RESET}")
    input("\nPress ENTER to exit...")
    sys.exit()

# -------------------------------
# TABULATE: MISSING ITEMS
# -------------------------------
missing_rows = []

for r in rows:
    if r["filename"] in filenames_with_missing:
        missing_rows.append([
            r["filename"],
            r["edi_check"],
            fmt(r["edi_amount"]),
            fmt(r["lockbox_amount"]),
            fmt(r["eft_amount"]),
            normalize_mmddyyyy(r["match_date"])
        ])

print(f"\n{YELLOW}--- Missing Items (Full File Listing) ---{RESET}\n")

print(tabulate(
    missing_rows,
    headers=["Filename", "Check#", "EDI Amt", "LB Amt", "EFT Amt", "Bank Date"],
    tablefmt="grid"
))

print(f"\nMissing rows found: {len(missing_rows)}")

input("\nPress ENTER to exit...")
