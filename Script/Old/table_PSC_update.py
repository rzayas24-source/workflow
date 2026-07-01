#!/usr/bin/env python3

import sqlite3
from datetime import datetime

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------
# ROBUST DATE NORMALIZATION
# -------------------------------

def normalize_mmddyyyy(s):
    """
    Normalize many common date formats to YYYY-MM-DD.
    Handles:
      - MM/DD/YYYY, MM/DD/YY
      - YYYY/MM/DD, YYYY-MM-DD
      - MM-DD-YYYY, MM-DD-YY
      - digits-only YYYYMMDD or MMDDYYYY
    """
    if not s:
        return None
    s = str(s).strip()

    fmts = [
        "%m/%d/%Y", "%m/%d/%y",
        "%Y/%m/%d", "%Y-%m-%d",
        "%m-%d-%Y", "%m-%d-%y",
        "%Y%m%d", "%m%d%Y",
    ]

    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.strftime("%Y-%m-%d")
        except:
            pass

    # digits-only fallback
    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 8:
        for f in ("%Y%m%d", "%m%d%Y"):
            try:
                dt = datetime.strptime(digits, f)
                return dt.strftime("%Y-%m-%d")
            except:
                pass

    # if already looks like YYYY-MM-DD, keep it
    if "-" in s and s.count("-") == 2:
        return s

    return None


def normalize_to_mmddyyyy(s):
    """Convert YYYY-MM-DD → MM/DD/YYYY"""
    if not s:
        return None
    if "-" in s:
        y, m, d = s.split("-")
        return f"{m}/{d}/{y}"
    return s

# -------------------------------
# GET CURRENT WORKDAY → BANK DAY
# -------------------------------

def get_current_workday():
    conn = get_conn()
    row = conn.execute("SELECT current_work_day FROM work_state WHERE id = 1").fetchone()
    conn.close()
    if row and row["current_work_day"]:
        return row["current_work_day"]
    return datetime.now().strftime("%Y-%m-%d")

def get_bank_day_for_workday(workday):
    conn = get_conn()
    rows = conn.execute("""
        SELECT bank_day, paperwork_day, is_closed, closure_reason
        FROM calendar
    """).fetchall()
    conn.close()

    normalized = []
    for bank_day, paperwork_day, is_closed, reason in rows:
        bank_norm = normalize_mmddyyyy(bank_day)
        paper_norm = normalize_mmddyyyy(paperwork_day)
        normalized.append((bank_norm, paper_norm, is_closed, reason))

    # Direct match
    for bank_norm, paper_norm, is_closed, reason in normalized:
        if paper_norm == workday:
            return bank_norm

    # Fallback: latest earlier bank_day
    earlier = [r for r in normalized if r[0] and r[0] < workday]
    earlier.sort(key=lambda r: r[0], reverse=True)
    return earlier[0][0] if earlier else workday

# -------------------------------
# MAIN REFRESH FUNCTION
# -------------------------------

def refresh_posting_screencapture():
    workday = get_current_workday()
    bank_day = get_bank_day_for_workday(workday)          # YYYY-MM-DD
    bank_day_mmdd = normalize_to_mmddyyyy(bank_day)       # MM/DD/YYYY

    print(f"\nRefreshing PostingScreenCapture for:")
    print(f"Workday: {workday}")
    print(f"Bank Day: {bank_day} ({bank_day_mmdd})\n")

    conn = get_conn()

    # Clear old snapshot
    conn.execute("DELETE FROM PostingScreenCapture WHERE date = ?", (bank_day_mmdd,))

    # EDI lookup
    edi_checks = set()
    try:
        edi_rows = conn.execute("SELECT edi_check FROM EDI_MatchResults").fetchall()
        for r in edi_rows:
            if r["edi_check"]:
                edi_checks.add(str(r["edi_check"]).strip())
    except:
        pass

    # -------------------------------
    # LOCKBOX
    # -------------------------------
    lock_rows = conn.execute("""
        SELECT [Check Number] AS chk,
               [Transaction Total] AS amt,
               [Deposit Date] AS d
        FROM Lockbox
    """).fetchall()

    for r in lock_rows:
        d_norm = normalize_mmddyyyy(r["d"])   # → YYYY-MM-DD
        if d_norm != bank_day:
            continue

        chk = str(r["chk"]).strip()
        amt = float(str(r["amt"]).replace(",", "").strip())
        edi_flag = "YES" if chk in edi_checks else "NO"

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'Lockbox', '', ?, ?, NULL, ?, NULL, ?, NULL)
        """, (chk, amt, bank_day_mmdd, edi_flag, amt))

    # -------------------------------
    # EFT
    # -------------------------------
    eft_rows = conn.execute("""
        SELECT Date AS d, Amount AS amt, CheckNumber AS chk, Payer AS payer
        FROM EFT
    """).fetchall()

    for r in eft_rows:
        d_norm = normalize_mmddyyyy(r["d"])   # → YYYY-MM-DD
        if d_norm != bank_day:
            continue

        chk = str(r["chk"]).strip()
        payer = str(r["payer"]).strip()
        amt = float(str(r["amt"]).replace(",", "").strip())
        edi_flag = "YES" if chk in edi_checks else "NO"

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EFT', ?, ?, ?, NULL, ?, NULL, NULL, ?)
        """, (chk, payer, amt, bank_day_mmdd, edi_flag, amt))

    # -------------------------------
    # EDI MATCH
    # -------------------------------
    edi_rows = conn.execute("""
        SELECT edi_check, edi_amount, lockbox_amount, eft_amount, match_date
        FROM EDI_MatchResults
    """).fetchall()

    for r in edi_rows:
        d_norm = normalize_mmddyyyy(r["match_date"])   # → YYYY-MM-DD
        if d_norm != bank_day:
            continue

        chk = str(r["edi_check"]).strip()
        edi_amt = float(str(r["edi_amount"]).replace(",", "").strip())
        lock_amt = r["lockbox_amount"]
        eft_amt = r["eft_amount"]

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EDI-MATCH', '', ?, ?, NULL, 'YES', ?, ?, ?)
        """, (chk, edi_amt, bank_day_mmdd, edi_amt, lock_amt, eft_amt))

    conn.commit()
    conn.close()

    print("PostingScreenCapture updated successfully.\n")
    input("Press ENTER to exit...")

# -------------------------------
# RUN
# -------------------------------

if __name__ == "__main__":
    refresh_posting_screencapture()
