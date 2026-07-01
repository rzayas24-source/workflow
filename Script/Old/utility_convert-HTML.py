#!/usr/bin/env python3

from db import get_conn   # ⭐ unified DB engine
import os
import shutil
import re
from datetime import datetime
from collections import defaultdict

HTML_EOB_FOLDER = r"C:\Renfrew\2.AVATAR\1_HTML-EOB"

# ------------------------------------------------------------
# DATE NORMALIZATION
# ------------------------------------------------------------

def normalize_mmddyyyy(s):
    if not s:
        return ""
    s = str(s).strip().replace("-", "/")

    fmts = ["%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d", "%m/%d/%y", "%Y%m%d"]
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


def normalize_to_yyyymmdd(s):
    try:
        return datetime.strptime(s, "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        return None

# ------------------------------------------------------------
# WORKDAY / BANK DAY
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# PSC REFRESH
# ------------------------------------------------------------

def refresh_posting_screencapture():
    workday = get_current_workday()              # MM/DD/YYYY
    bank_day = get_bank_day_for_workday(workday) # MM/DD/YYYY

    print("\n===================================================")
    print(" REFRESHING PostingScreenCapture")
    print("===================================================")
    print(f"Posting Day (Paperwork Day): {workday}")
    print(f"Bank Day (Actual Posting):  {bank_day}")
    print("---------------------------------------------------\n")

    conn = get_conn()

    conn.execute("DELETE FROM PostingScreenCapture WHERE date = ?", (bank_day,))

    # Load EDI checks
    edi_checks = set()
    try:
        edi_rows = conn.execute("SELECT edi_check FROM EDI_MatchResults").fetchall()
        for r in edi_rows:
            if r["edi_check"]:
                edi_checks.add(str(r["edi_check"]).strip())
    except:
        pass

    # LOCKBOX
    lock_rows = conn.execute("""
        SELECT [Check Number] AS chk,
               [Transaction Total] AS amt,
               [Deposit Date] AS d
        FROM Lockbox
    """).fetchall()

    for r in lock_rows:
        d_norm = normalize_mmddyyyy(r["d"])
        if d_norm != bank_day:
            continue

        chk = str(r["chk"]).strip()
        amt = float(str(r["amt"]).replace(",", "").strip())
        edi_flag = "YES" if chk in edi_checks else "NO"

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date,
             file_number, edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'Lockbox', '', ?, ?, NULL, ?, NULL, ?, NULL)
        """, (chk, amt, bank_day, edi_flag, amt))

    # EFT
    eft_rows = conn.execute("""
        SELECT Date AS d, Amount AS amt, CheckNumber AS chk, Payer AS payer
        FROM EFT
    """).fetchall()

    for r in eft_rows:
        d_norm = normalize_mmddyyyy(r["d"])
        if d_norm != bank_day:
            continue

        chk = str(r["chk"]).strip()
        payer = str(r["payer"]).strip()
        amt = float(str(r["amt"]).replace(",", "").strip())
        edi_flag = "YES" if chk in edi_checks else "NO"

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date,
             file_number, edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EFT', ?, ?, ?, NULL, ?, NULL, NULL, ?)
        """, (chk, payer, amt, bank_day, edi_flag, amt))

    # EDI MATCH
    edi_rows = conn.execute("""
        SELECT edi_check, edi_amount, lockbox_amount, eft_amount, match_date
        FROM EDI_MatchResults
    """).fetchall()

    for r in edi_rows:
        d_norm = normalize_mmddyyyy(r["match_date"])
        if d_norm != bank_day:
            continue

        chk = str(r["edi_check"]).strip()
        edi_amt = float(str(r["edi_amount"]).replace(",", "").strip())
        lock_amt = r["lockbox_amount"]
        eft_amt = r["eft_amount"]

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date,
             file_number, edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EDI-MATCH', '', ?, ?, NULL, 'YES', ?, ?, ?)
        """, (chk, edi_amt, bank_day, edi_amt, lock_amt, eft_amt))

    conn.commit()
    conn.close()

    print("PostingScreenCapture updated successfully.\n")

# ------------------------------------------------------------
# LOAD PSC SNAPSHOT
# ------------------------------------------------------------

def load_psc_snapshot(bank_day):
    conn = get_conn()
    rows = conn.execute("""
        SELECT check_number, source_type, amount, date
        FROM PostingScreenCapture
        WHERE check_number IS NOT NULL AND check_number != ''
          AND date = ?
    """, (bank_day,)).fetchall()
    conn.close()

    psc = {}
    for r in rows:
        chk = str(r["check_number"]).strip()
        psc[chk] = {
            "source_type": r["source_type"],
            "amount": r["amount"],
            "date": r["date"],
        }
    return psc

# ------------------------------------------------------------
# MAIN VERIFICATION + RENAME
# ------------------------------------------------------------

def scan_and_rename_html_eobs():

    workday = get_current_workday()
    if not workday:
        print("ERROR: No current work day is set.")
        input("\nPress ENTER to exit...")
        return

    bank_day = get_bank_day_for_workday(workday)
    if not bank_day:
        print(f"ERROR: Could not map paperwork day {workday} to a bank day.")
        input("\nPress ENTER to exit...")
        return

    print("\n===================================================")
    print(" HTML EOB RENAME — VERIFICATION LAYER")
    print("===================================================\n")
    print(f"Posting Day (Paperwork): {workday}")
    print(f"Bank Day (Actual):       {bank_day}")
    print("---------------------------------------------------\n")

    print("Refreshing PostingScreenCapture...")
    refresh_posting_screencapture()

    psc = load_psc_snapshot(bank_day)
    if not psc:
        print("ERROR: PSC is empty for this bank day.")
        input("\nPress ENTER to exit...")
        return

    html_files = [
        f for f in os.listdir(HTML_EOB_FOLDER)
        if f.lower().endswith(".html")
    ]

    if not html_files:
        print("No HTML EOB files found.")
        input("\nPress ENTER to exit...")
        return

    print("A. HTML EOB FILES (ACTUAL)")
    print("---------------------------------------------------")

    verification = []
    groups = defaultdict(list)

    for fname in html_files:
        full_path = os.path.join(HTML_EOB_FOLDER, fname)

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                contents = f.read()
        except:
            contents = ""

        matched_checks = [chk for chk in psc if chk in contents]

        if len(matched_checks) == 1:
            status = "YES"
        elif len(matched_checks) > 1:
            status = "MULTI-MATCH"
        else:
            status = "NO"

        verification.append({
            "file": fname,
            "matches": matched_checks,
            "status": status
        })

        key = (tuple(matched_checks) if matched_checks else ("NONE",), status)
        groups[key].append(fname)

    for (checks, status), file_list in groups.items():
        for fname in file_list:
            print(f"File: {fname}")

        checks_str = ", ".join(checks) if checks != ("NONE",) else "NONE"
        print(f"  → Matches: {checks_str}")
        print(f"  → Status:  {status}")
        print(f"  → {len(file_list)} item(s)\n")

    print("---------------------------------------------------\n")

    print("B. POSTING SCREEN CAPTURE (EXPECTED)")
    print("---------------------------------------------------")
    for chk, meta in sorted(psc.items(), key=lambda x: x[0]):
        print(
            f"Check#: {chk:<10}  "
            f"Source: {meta['source_type']:<10}  "
            f"Amount: {meta['amount']:<10}  "
            f"Date: {meta['date']}"
        )
    print("---------------------------------------------------\n")

    matches = sum(1 for v in verification if v["status"] == "YES")
    multi = sum(1 for v in verification if v["status"] == "MULTI-MATCH")
    nomatch = sum(1 for v in verification if v["status"] == "NO")

    print("C. SUMMARY")
    print("---------------------------------------------------")
    print(f"Matches:       {matches}")
    print(f"Multi-Matches: {multi}")
    print(f"No Matches:    {nomatch}")
    print("---------------------------------------------------\n")

    choice = input("Proceed with renaming? (Y/N): ").strip().upper()
    if choice != "Y":
        print("\nRename aborted by user.")
        input("\nPress ENTER to exit...")
        return

    print("\nRenaming files...\n")
    for v in verification:
        if v["status"] != "YES":
            continue

        chk = v["matches"][0]
        old_path = os.path.join(HTML_EOB_FOLDER, v["file"])
        new_name = f"835-{chk}.html"
        new_path = os.path.join(HTML_EOB_FOLDER, new_name)

        counter = 1
        while os.path.exists(new_path):
            new_name = f"835-{chk}-{counter}.html"
            new_path = os.path.join(HTML_EOB_FOLDER, new_name)
            counter += 1

        shutil.move(old_path, new_path)
        print(f"[RENAMED] {v['file']} → {new_name}")

    print("\nHTML EOB rename process completed successfully.")
    input("\nPress ENTER to exit...")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

if __name__ == "__main__":
    scan_and_rename_html_eobs()
