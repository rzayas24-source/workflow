#!/usr/bin/env python3

import sqlite3
import sys
from datetime import datetime
from tabulate import tabulate   # <-- ADDED

# Ensure parent folder is visible for imports if needed
sys.path.append(r"C:\Renfrew\Workflow")

DB_PATH = r"C:\Renfrew\Workflow\database.db"

# ANSI Colors
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

print(">>> EDI / Lockbox / EFT Match Viewer (with Filename)")
print("--------------------------------------------------")

# -------------------------------
# DATE NORMALIZER (MM/DD/YYYY)
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

    return s  # fallback

# -------------------------------
# DB CONNECTION
# -------------------------------
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# -------------------------------
# MAIN QUERY (NOW WITH FILENAME)
# -------------------------------
rows = cur.execute("""
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
ORDER BY e.filename, e.check_number;
""").fetchall()

conn.close()

# -------------------------------
# BUILD TABULATE TABLE
# -------------------------------
table_data = []

for r in rows:

    # Lockbox amount
    try:
        lb = f"{float(r['lockbox_amount']):,.2f}" if r['lockbox_amount'] else ""
    except:
        lb = r['lockbox_amount'] or ""

    # EFT amount
    try:
        eft = f"{float(r['eft_amount']):,.2f}" if r['eft_amount'] else ""
    except:
        eft = r['eft_amount'] or ""

    dt = normalize_mmddyyyy(r['match_date'])

    table_data.append([
        r["filename"] or "",
        r["edi_check"] or "",
        lb,
        eft,
        dt
    ])

# -------------------------------
# DISPLAY USING TABULATE
# -------------------------------
print()
print(tabulate(
    table_data,
    headers=["Filename", "EDI Check", "Lockbox", "EFT", "Date"],
    tablefmt="grid"
))
print()

print(f">>> Total rows returned: {len(table_data)}")
print(">>> Match display complete.")

input("Press ENTER to exit...")
