"""
system_posting_core.py
Posting screen + capture + CSV export.

Contains:
- Posting screen builder
- EFT / Lockbox / EDI display
- Subtotals
- PostingScreenCapture writer
- CSV export

Does NOT contain:
- Calendar logic
- EDI rebuild logic
- CLI
"""

import csv
import os
import traceback

from db import get_conn   # ⭐ dynamic DB connection

from system_calendar_core import (
    normalize_mmddyyyy,
    get_current_work_day,
)

from system_EMR_core import (
    rebuild_edi_matchresults_core,
)

EXPORT_FOLDER = r"C:\Renfrew\Workflow\DB_Exports"


# ============================================================
#   POSTING SCREEN CAPTURE
# ============================================================

def save_posting_to_capture(bank_day_norm, lock_items, eft_items, edi_rows, edi_checks):
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {cursor.description[i][0]: row[i] for i in range(len(row))}

    conn.execute("DELETE FROM PostingScreenCapture WHERE date = ?", (bank_day_norm,))

    # LOCKBOX
    for amt, chk in lock_items:
        edi_flag = "YES" if chk in edi_checks else "NO"
        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'LOCKBOX', '', ?, ?, NULL, ?, NULL, ?, NULL)
        """, (chk, amt, bank_day_norm, edi_flag, amt))

    # EFT
    for amt, chk, payer in eft_items:
        edi_flag = "YES" if chk in edi_checks else "NO"
        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EFT', ?, ?, ?, NULL, ?, NULL, NULL, ?)
        """, (chk, payer, amt, bank_day_norm, edi_flag, amt))

    # EDI MATCH
    for r in edi_rows:
        m_norm = normalize_mmddyyyy(r["match_date"])
        if not m_norm or m_norm != bank_day_norm:
            continue

        conn.execute("""
            INSERT INTO PostingScreenCapture
            (check_number, source_type, payer_name, amount, date, file_number,
             edi_match, edi_amount, lockbox_amount, eft_amount)
            VALUES (?, 'EDI-MATCH', '', ?, ?, NULL, 'YES', ?, ?, ?)
        """, (
            r["edi_check"],
            r["edi_amount"],
            bank_day_norm,
            r["edi_amount"],
            r["lockbox_amount"],
            r["eft_amount"]
        ))

    conn.commit()
    conn.close()


# ============================================================
#   POSTING SCREEN
# ============================================================

def show_items_for_workday(workday_str):
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    conn = get_conn()
    conn.row_factory = lambda cursor, row: {cursor.description[i][0]: row[i] for i in range(len(row))}

    try:
        # Always rebuild EDI matches before showing posting screen
        rebuild_edi_matchresults_core()

        # Get bank day for this paperwork day
        row = conn.execute(
            "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
            (workday_str,)
        ).fetchone()

        if not row:
            print(f"No calendar entry found for paperwork day {workday_str}")
            return

        bank_day = row["bank_day"]
        bank_day_norm = normalize_mmddyyyy(bank_day) or bank_day
        current_work = get_current_work_day()

        print(f"\n{CYAN}====================================")
        print(f"   ITEMS FOR WORKDAY {workday_str}")
        print(f"   BANK DAY: {bank_day}")
        if current_work and current_work == workday_str:
            print(f"{YELLOW}   CURRENT WORK DAY{RESET}")
        print(f"{CYAN}===================================={RESET}\n")

        subtotal_lock = 0.0
        subtotal_eft = 0.0
        subtotal_edi_match = 0.0
        count_lock = 0
        count_eft = 0
        count_edi_match = 0

        # Build EDI lookup set — ONLY real matches for THIS bank day
        edi_checks = set()
        try:
            edi_lookup_rows = conn.execute("""
                SELECT edi_check
                FROM EDI_MatchResults
                WHERE match_date = ?
                  AND (eft_amount > 0 OR lockbox_amount > 0)
            """, (bank_day_norm,)).fetchall()
            for r in edi_lookup_rows:
                if r["edi_check"]:
                    edi_checks.add(str(r["edi_check"]).strip())
        except Exception:
            edi_checks = set()

        def _fmt_amt(v):
            try:
                if v is None or v == "":
                    return ""
                s = str(v).replace(",", "").strip()
                return f"{float(s):,.2f}"
            except Exception:
                return str(v)

        # ----------------------------------------------------
        # LOCKBOX
        # ----------------------------------------------------
        try:
            lockbox_rows = conn.execute("""
                SELECT [Check Number] AS check_number,
                       [Transaction Total] AS amount,
                       [Deposit Date] AS deposit_date
                FROM Lockbox
            """).fetchall()
        except Exception:
            print("Warning: could not read Lockbox table or columns.")
            lockbox_rows = []

        print(f"{YELLOW}----- LOCKBOX -----{RESET}")
        lock_items = []

        for r in lockbox_rows:
            d_norm = normalize_mmddyyyy(r["deposit_date"])
            if not d_norm or d_norm != bank_day_norm:
                continue

            try:
                amt_raw = r["amount"]
                amt = float(str(amt_raw).replace(",", "").strip()) if amt_raw not in (None, "") else 0.0
            except Exception:
                amt = 0.0

            chk = str(r["check_number"]).strip() if r["check_number"] else ""
            lock_items.append((amt, chk))
            subtotal_lock += amt
            count_lock += 1

        lock_items.sort(reverse=True, key=lambda x: x[0])

        if lock_items:
            for amt, chk in lock_items:
                edi_flag = "YES" if chk in edi_checks else ""
                line = (
                    f"Amount: {_fmt_amt(amt):>12}   "
                    f"Check#: {chk:<20}   "
                    f"EDI: {edi_flag:<3}"
                )
                if edi_flag == "YES":
                    print(f"{YELLOW}{line}{RESET}")
                else:
                    print(line)
        else:
            print("(no lockbox rows for this bank day)")

        print(f"\nLockbox subtotal: {subtotal_lock:,.2f}")
        print(f"Row count: {count_lock}\n")

        # ----------------------------------------------------
        # EFT
        # ----------------------------------------------------
        try:
            eft_rows = conn.execute("""
                SELECT Date AS as_of_date,
                       Amount AS credit_amt,
                       CheckNumber AS check_number,
                       Payer AS payer_name
                FROM EFT
            """).fetchall()
        except Exception:
            print("Warning: could not read EFT table or columns.")
            eft_rows = []

        print(f"{YELLOW}----- EFT -----{RESET}")
        eft_items = []

        for r in eft_rows:
            d_norm = normalize_mmddyyyy(r["as_of_date"])
            if not d_norm or d_norm != bank_day_norm:
                continue

            try:
                amt_raw = r["credit_amt"]
                amt = float(str(amt_raw).replace(",", "").strip()) if amt_raw not in (None, "") else 0.0
            except Exception:
                amt = 0.0

            chk = str(r["check_number"]).strip() if r["check_number"] else ""
            payer = str(r["payer_name"]).strip() if r["payer_name"] else ""

            eft_items.append((amt, chk, payer))
            subtotal_eft += amt
            count_eft += 1

        eft_items.sort(key=lambda x: (x[2].lower() if x[2] else ""))

        if eft_items:
            for amt, chk, payer in eft_items:
                edi_flag = "YES" if chk in edi_checks else ""
                line = (
                    f"Amount: {_fmt_amt(amt):>12}   "
                    f"Check#: {chk:<20}   "
                    f"Payer: {payer:<22}   "
                    f"EDI: {edi_flag:<3}"
                )
                if edi_flag == "YES":
                    print(f"{YELLOW}{line}{RESET}")
                else:
                    print(line)
        else:
            print("(no EFT rows for this bank day)")

        print(f"\nEFT subtotal: {subtotal_eft:,.2f}")
        print(f"Row count: {count_eft}\n")

        # ----------------------------------------------------
        # EDI MATCH RESULTS
        # ----------------------------------------------------
        try:
            edi_rows = conn.execute("""
                SELECT edi_check, edi_amount, lockbox_amount, eft_amount, match_date
                FROM EDI_MatchResults
                WHERE match_date = ?
            """, (bank_day_norm,)).fetchall()
        except Exception:
            print("Warning: could not read EDI_MatchResults table or columns.")
            edi_rows = []

        print(f"{YELLOW}----- EDI MATCH RESULTS -----{RESET}")

        for r in edi_rows:
            m_norm = normalize_mmddyyyy(r["match_date"])
            if not m_norm or m_norm != bank_day_norm:
                continue

            try:
                amt_raw = r["edi_amount"]
                amt = float(str(amt_raw).replace(",", "").strip()) if amt_raw not in (None, "") else 0.0
            except Exception:
                amt = 0.0

            chk = str(r["edi_check"]).strip() if r["edi_check"] else ""
            lock_amt_str = _fmt_amt(r["lockbox_amount"])
            eft_amt_str = _fmt_amt(r["eft_amount"])

            print(
                f"Amount: {_fmt_amt(amt):>12}   "
                f"Check#: {chk:<20}   "
                f"Lockbox: {lock_amt_str:<12}   "
                f"EFT: {eft_amt_str:<12}"
            )

            subtotal_edi_match += amt
            count_edi_match += 1

        if count_edi_match == 0:
            print("(no EDI match rows for this bank day)")

        print(f"\nEDI-MATCH subtotal: {subtotal_edi_match:,.2f}")
        print(f"Row count: {count_edi_match}\n")

        # Save posting screen snapshot
        save_posting_to_capture(
            bank_day_norm,
            lock_items,
            eft_items,
            edi_rows,
            edi_checks
        )

    except Exception:
        print("An unexpected error occurred while building the posting screen:")
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print(f"{CYAN}===================================={RESET}")
    print("               TOTALS")
    print(f"{CYAN}===================================={RESET}")
    print(f"Lockbox Total: {subtotal_lock:,.2f}")
    print(f"EFT Total:     {subtotal_eft:,.2f}")
    print(f"EDI-MATCH Total: {subtotal_edi_match:,.2f}")
    if abs(subtotal_lock - subtotal_eft) < 0.005:
        print(f"{GREEN}MATCHED ✔ (Lockbox vs EFT){RESET}")
    print(f"{CYAN}===================================={RESET}\n")


# ============================================================
#   EXPORT POSTING TO CSV
# ============================================================

def export_posting_to_csv(workday_str):
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {cursor.description[i][0]: row[i] for i in range(len(row))}

    os.makedirs(EXPORT_FOLDER, exist_ok=True)

    row = conn.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (workday_str,)
    ).fetchone()

    if not row:
        print(f"No calendar entry found for paperwork day {workday_str}")
        conn.close()
        return

    bank_day = row["bank_day"]
    bank_day_norm = normalize_mmddyyyy(bank_day) or bank_day

    safe_date = bank_day_norm.replace("/", "")
    csv_path = os.path.join(EXPORT_FOLDER, f"posting_{safe_date}.csv")

    rows_out = []

    # Build EDI lookup set — ONLY real matches for THIS bank day
    edi_checks = set()
    try:
        edi_lookup_rows = conn.execute("""
            SELECT edi_check
            FROM EDI_MatchResults
            WHERE match_date = ?
              AND (eft_amount > 0 OR lockbox_amount > 0)
        """, (bank_day_norm,)).fetchall()
        for r in edi_lookup_rows:
            if r["edi_check"]:
                edi_checks.add(str(r["edi_check"]).strip())
    except Exception:
        edi_checks = set()

    # LOCKBOX
    try:
        lockbox_rows = conn.execute("""
            SELECT [Check Number] AS check_number,
                   [Transaction Total] AS amount,
                   [Deposit Date] AS deposit_date
            FROM Lockbox
        """).fetchall()
    except Exception:
        lockbox_rows = []

    for r in lockbox_rows:
        d_norm = normalize_mmddyyyy(r["deposit_date"])
        if not d_norm or d_norm != bank_day_norm:
            continue
        chk = str(r["check_number"]).strip() if r["check_number"] else ""
        edi_flag = "YES" if chk in edi_checks else ""
        rows_out.append({
            "Source": "Lockbox",
            "Amount": r["amount"],
            "Check#": chk,
            "Payer": "",
            "EDI": edi_flag
        })

    # EFT
    try:
        eft_rows = conn.execute("""
            SELECT Date AS as_of_date,
                   Amount AS credit_amt,
                   CheckNumber AS check_number,
                   Payer AS payer_name
            FROM EFT
        """).fetchall()
    except Exception:
        eft_rows = []

    for r in eft_rows:
        d_norm = normalize_mmddyyyy(r["as_of_date"])
        if not d_norm or d_norm != bank_day_norm:
            continue
        chk = str(r["check_number"]).strip() if r["check_number"] else ""
        edi_flag = "YES" if chk in edi_checks else ""
        rows_out.append({
            "Source": "EFT",
            "Amount": r["credit_amt"],
            "Check#": chk,
            "Payer": r["payer_name"] or "",
            "EDI": edi_flag
        })

    # EDI MATCH
    try:
        edi_rows = conn.execute("""
            SELECT edi_check, edi_amount, lockbox_amount, eft_amount, match_date
            FROM EDI_MatchResults
            WHERE match_date = ?
        """, (bank_day_norm,)).fetchall()
    except Exception:
        edi_rows = []

    for r in edi_rows:
        m_norm = normalize_mmddyyyy(r["match_date"])
        if not m_norm or m_norm != bank_day_norm:
            continue
        chk = str(r["edi_check"]).strip() if r["edi_check"] else ""
        rows_out.append({
            "Source": "EDI-Match",
            "Amount": r["edi_amount"],
            "Check#": chk,
            "Payer": "",
            "EDI": ""
        })

    conn.close()

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Source", "Amount", "Check#", "Payer", "EDI"])
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"\nPosting exported to:\n{csv_path}")
