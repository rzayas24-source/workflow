#!/usr/bin/env python3

from db import get_conn
import re
import os
from datetime import datetime

ERA_FOLDER = r"C:\Renfrew\2.AVATAR\2_ERA-835"

# --------------------------------------------------
# DATE NORMALIZATION
# --------------------------------------------------

def normalize_mmddyyyy(s):
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

    digits = "".join(c for c in s if c.isdigit())
    if len(digits) == 8:
        for f in ("%Y%m%d", "%m%d%Y"):
            try:
                dt = datetime.strptime(digits, f)
                return dt.strftime("%Y-%m-%d")
            except:
                pass

    if "-" in s and s.count("-") == 2:
        return s

    return None


def normalize_to_mmddyyyy(s):
    if not s:
        return None
    if "-" in s:
        y, m, d = s.split("-")
        return f"{m}/{d}/{y}"
    return s

# --------------------------------------------------
# WORKDAY / BANK DAY
# --------------------------------------------------

def get_current_workday():
    conn = get_conn()
    row = conn.execute(
        "SELECT current_work_day FROM work_state WHERE id = 1"
    ).fetchone()
    conn.close()
    if row and row["current_work_day"]:
        norm = normalize_mmddyyyy(row["current_work_day"])
        return norm if norm else row["current_work_day"]
    return datetime.now().strftime("%Y-%m-%d")


def get_bank_day_for_workday(workday):
    conn = get_conn()
    rows = conn.execute("""
        SELECT bank_day, paperwork_day
        FROM calendar
    """).fetchall()
    conn.close()

    normalized = []
    for r in rows:
        bank_norm = normalize_mmddyyyy(r["bank_day"])
        paper_norm = normalize_mmddyyyy(r["paperwork_day"])
        normalized.append((bank_norm, paper_norm))

    for bank_norm, paper_norm in normalized:
        if paper_norm == workday:
            return bank_norm

    earlier = [r for r in normalized if r[0] and r[0] < workday]
    earlier.sort(key=lambda r: r[0], reverse=True)
    return earlier[0][0] if earlier else workday

# --------------------------------------------------
# PSC REFRESH
# --------------------------------------------------

def refresh_posting_screencapture():
    workday = get_current_workday()
    bank_day = get_bank_day_for_workday(workday)
    bank_day_mmdd = normalize_to_mmddyyyy(bank_day)

    print("\n===================================================")
    print(" REFRESHING PostingScreenCapture")
    print("===================================================")
    print(f"Posting Day (Paperwork Day): {normalize_to_mmddyyyy(workday)}")
    print(f"Bank Day (Actual Posting):  {bank_day_mmdd}")
    print("---------------------------------------------------\n")

    conn = get_conn()

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
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'Lockbox', '', ?, ?, ?, NULL, ?, NULL)
        """, (chk, amt, bank_day_mmdd, edi_flag, amt))

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
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EFT', ?, ?, ?, ?, NULL, NULL, ?)
        """, (chk, payer, amt, bank_day_mmdd, edi_flag, amt))

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
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EDI-MATCH', '', ?, ?, 'YES', ?, ?, ?)
        """, (chk, edi_amt, bank_day_mmdd, edi_amt, lock_amt, eft_amt))

    conn.commit()
    conn.close()

    print("PostingScreenCapture updated.\n")

# --------------------------------------------------
# ERA CHECK EXTRACTION
# --------------------------------------------------

CHECK_PATTERN_BPR = re.compile(r"BPR\*I\*[^*]*\*C\*CHK\*([0-9A-Za-z]+)\*")
CHECK_PATTERN_TRN = re.compile(r"TRN\*1\*([0-9A-Za-z]+)\*")

def extract_checks_from_era_file(path):
    checks = set()
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        for m in CHECK_PATTERN_BPR.finditer(text):
            checks.add(m.group(1))

        for m in CHECK_PATTERN_TRN.finditer(text):
            checks.add(m.group(1))

    except Exception as e:
        print(f"Error reading {path}: {e}")

    return sorted(checks)

# --------------------------------------------------
# LOAD PSC SNAPSHOT
# --------------------------------------------------

def load_psc_snapshot(bank_day_mmdd):
    conn = get_conn()
    rows = conn.execute("""
        SELECT check_number, source_type
        FROM PostingScreenCapture
        WHERE date = ?
    """, (bank_day_mmdd,)).fetchall()
    conn.close()

    psc = {}
    for r in rows:
        chk = str(r["check_number"]).strip()
        psc[chk] = r["source_type"]
    return psc

# --------------------------------------------------
# ERA RENAME LOGIC (GLOBAL COUNTER + MULTI-CHECK NAMES)
# --------------------------------------------------

def run_verification_and_rename():
    workday = get_current_workday()
    bank_day = get_bank_day_for_workday(workday)
    bank_day_mmdd = normalize_to_mmddyyyy(bank_day)

    refresh_posting_screencapture()
    psc = load_psc_snapshot(bank_day_mmdd)

    # Only EDI rows matter
    psc_edi_checks = [
        chk for chk, stype in psc.items()
        if stype.upper().startswith("EDI")
    ]

    era_files = [
        f for f in os.listdir(ERA_FOLDER)
        if f.lower().endswith(".txt")
    ]

    print("\n===================================================")
    print(" ERA RENAME PROCESS")
    print("===================================================\n")

    # Preload ERA file check maps
    era_map = {}
    for fname in era_files:
        full = os.path.join(ERA_FOLDER, fname)
        era_map[fname] = extract_checks_from_era_file(full)

    used_files = set()      # prevent double-renaming
    global_idx = 1          # GLOBAL 835 counter

    # For each PSC EDI check, find matching ERA files
    for chk in psc_edi_checks:
        matches = []

        for fname, checks in era_map.items():
            if fname in used_files:
                continue
            if chk in checks:
                matches.append(fname)

        if not matches:
            print(f"❌ No ERA file found for EDI check {chk}")
            continue

        # Rename matches using GLOBAL counter
        for fname in matches:
            old_path = os.path.join(ERA_FOLDER, fname)
            checks_in_file = era_map[fname]

            # If multiple checks in the ERA file, include them all: <check1>,<check2>,...
            if len(checks_in_file) > 1:
                checks_suffix = ",".join(checks_in_file)
            else:
                checks_suffix = chk  # single check, just use PSC check

            new_name = f"835-{global_idx}-{checks_suffix}.txt"
            new_path = os.path.join(ERA_FOLDER, new_name)

            try:
                os.rename(old_path, new_path)
                print(f"✔ Renamed: {fname} → {new_name}")
                used_files.add(fname)
                global_idx += 1
            except FileNotFoundError:
                print(f"⚠ Skipped missing file (already renamed earlier): {fname}")

    print("\nDone.\n")

# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    run_verification_and_rename()
