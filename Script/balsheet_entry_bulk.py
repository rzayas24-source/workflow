#!/usr/bin/env python3

from db import get_conn
from datetime import datetime

# ---------------------------------------------------------
# ROBUST DATE NORMALIZATION
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# WORKDAY / BANKDAY LOOKUPS
# ---------------------------------------------------------

def get_current_workday_raw(conn):
    row = conn.execute("SELECT current_work_day FROM work_state WHERE id = 1").fetchone()
    if row and row["current_work_day"]:
        return row["current_work_day"]
    return datetime.now().strftime("%Y-%m-%d")

def get_bank_day_for_refresh(conn, workday):
    rows = conn.execute("""
        SELECT bank_day, paperwork_day
        FROM calendar
    """).fetchall()

    normalized = []
    for bank_day, paperwork_day in rows:
        bank_norm = normalize_mmddyyyy(bank_day)
        paper_norm = normalize_mmddyyyy(paperwork_day)
        normalized.append((bank_norm, paper_norm))

    for bank_norm, paper_norm in normalized:
        if paper_norm == workday:
            return bank_norm

    earlier = [r for r in normalized if r[0] < workday]
    if not earlier:
        raise SystemExit("\nERROR: No earlier bank_day exists in calendar.")
    earlier.sort(key=lambda r: r[0], reverse=True)
    return earlier[0][0]

# ---------------------------------------------------------
# REFRESH POSTINGSCREENCAPTURE
# ---------------------------------------------------------

def refresh_posting_screencapture(conn):
    workday_raw = get_current_workday_raw(conn)
    workday = normalize_mmddyyyy(workday_raw)

    bank_day = get_bank_day_for_refresh(conn, workday)
    bank_day_mmdd = normalize_to_mmddyyyy(bank_day)

    print(f"\nRefreshing PostingScreenCapture for:")
    print(f"Workday: {workday_raw} → normalized {workday}")
    print(f"Bank Day: {bank_day} ({bank_day_mmdd})\n")

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
        if normalize_mmddyyyy(r["d"]) != bank_day:
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

    # EFT
    eft_rows = conn.execute("""
        SELECT Date AS d, Amount AS amt, CheckNumber AS chk, Payer AS payer
        FROM EFT
    """).fetchall()

    for r in eft_rows:
        eft_norm = normalize_mmddyyyy(r["d"])
        if eft_norm != bank_day:
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

    # EDI MATCH
    edi_rows = conn.execute("""
        SELECT edi_check, edi_amount, lockbox_amount, eft_amount, match_date
        FROM EDI_MatchResults
    """).fetchall()

    for r in edi_rows:
        if normalize_mmddyyyy(r["match_date"]) != bank_day:
            continue

        chk = str(r["edi_check"]).strip()
        edi_amt = float(str(r["edi_amount"]).replace(",", "").strip())

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EDI-MATCH', '', ?, ?, NULL, 'YES', ?, ?, ?)
        """, (
            chk,
            edi_amt,
            bank_day_mmdd,
            edi_amt,
            r["lockbox_amount"],
            r["eft_amount"]
        ))

    print(f"PostingScreenCapture refreshed for bank day {bank_day_mmdd}.\n")

# ---------------------------------------------------------
# ID GENERATOR
# ---------------------------------------------------------

def get_next_entry_id(conn, posting_date):
    date_key = posting_date.replace("-", "")
    row = conn.execute("SELECT GenID FROM ControlsTools WHERE id = 1").fetchone()

    if row is None:
        current_seq = 0
        conn.execute("INSERT INTO ControlsTools (id, GenID) VALUES (1, 0)")
    else:
        current_seq = row["GenID"]

    next_seq = current_seq + 1
    conn.execute("UPDATE ControlsTools SET GenID = ? WHERE id = 1", (next_seq,))

    return f"{date_key}-{next_seq}"

# ---------------------------------------------------------
# SAFETY CHECK
# ---------------------------------------------------------

def safety_check_posting_date(conn, bank_day):
    row = conn.execute("SELECT COUNT(*) AS c FROM Balsheet WHERE PostingDate = ?", (bank_day,)).fetchone()

    if row["c"] > 0:
        print("\n=== SAFETY CHECK FAILED ===")
        print(f"Bank day {bank_day} already exists in Balsheet.")
        input("\nPress Enter to exit...")
        raise SystemExit

    print(f"Safety check passed. No entries exist for {bank_day}.")
    return True

# ---------------------------------------------------------
# DUPLICATE CHECK
# ---------------------------------------------------------

def balsheet_exists(conn, amount, payer, check_number, bank_day):
    row = conn.execute("""
        SELECT EntryID FROM Balsheet
        WHERE Amount = ?
          AND Payer = ?
          AND "Check Number" = ?
          AND PostingDate = ?
    """, (amount, payer, check_number, bank_day)).fetchone()
    return row is not None

# ---------------------------------------------------------
# MAIN LOADER
# ---------------------------------------------------------

def load_eft_lockbox_into_balsheet(conn):
    workday = get_current_workday_raw(conn)
    workday = normalize_mmddyyyy(workday)

    print("\n=== AUTO‑POSTING EFT/LOCKBOX INTO BALSHEET ===")
    print(f"Workday: {workday}")

    bank_day = get_bank_day_for_refresh(conn, workday)
    print(f"Bank Day Used: {bank_day}")

    safety_check_posting_date(conn, bank_day)

    rows = conn.execute("""
        SELECT id, check_number, source_type, payer_name, amount, edi_match
        FROM PostingScreenCapture
        WHERE source_type IN ('EFT', 'Lockbox')
    """).fetchall()

    print(f"Found {len(rows)} EFT/Lockbox rows to evaluate.\n")

    inserted = 0
    skipped = 0

    for rec in rows:
        check_number = rec["check_number"]
        source_type = rec["source_type"]
        payer_name = rec["payer_name"]
        amount = rec["amount"]

        balsheet_type = "E" if source_type == "EFT" else "L"

        edi_flag = "Y" if rec["edi_match"] == "YES" else "N"

        if edi_flag == "Y":
            poster = "R"
            nick_amt = 0.0
            raul_amt = amount
        else:
            poster = "N"
            nick_amt = amount
            raul_amt = 0.0

        if balsheet_exists(conn, amount, payer_name, check_number, bank_day):
            print(f"SKIP: Already exists → {payer_name} | {check_number} | {amount}")
            skipped += 1
            continue

        entry_id = get_next_entry_id(conn, bank_day)

        conn.execute("""
            INSERT INTO Balsheet (
                EntryID, PostingDate, Type, Amount, Payer, "Check Number",
                EDI, Poster, EOB, UnPosted, Misc, "Misc-Type", Notes,
                Nick, Raul, Needs, "From", "To"
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id, bank_day, balsheet_type, amount, payer_name,
            check_number, edi_flag, poster, "", 0.0, 0.0, "", "",
            nick_amt, raul_amt, "", "", ""
        ))

        print(f"INSERTED: {entry_id} | {payer_name} | {check_number} | {amount} | EDI={edi_flag} | Poster={poster}")
        inserted += 1

    print("\n=== SUMMARY ===")
    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")
    print("Done.\n")

    input("Press Enter to exit...")

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":
    conn = get_conn()
    refresh_posting_screencapture(conn)
    load_eft_lockbox_into_balsheet(conn)
    conn.commit()
    conn.close()
