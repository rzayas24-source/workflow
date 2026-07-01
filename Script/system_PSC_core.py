#!/usr/bin/env python3

from db import get_conn
from system_calendar_core import (
    get_current_work_day,
    normalize_mmddyyyy
)
from system_EMR_core import rebuild_edi_matchresults_core
from system_posting_core import show_items_for_workday


def resolve_work_and_bank_day():
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    workday = get_current_work_day()
    if not workday:
        print("[PSC] ERROR: No current work day set.")
        conn.close()
        return None, None

    row = cur.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (workday,)
    ).fetchone()

    conn.close()

    if not row:
        print(f"[PSC] ERROR: No calendar entry for paperwork day {workday}")
        return workday, None

    bank_day = normalize_mmddyyyy(row["bank_day"]) or row["bank_day"]
    return workday, bank_day


def run_psc_core():
    print("\n[PSC] Step 1 — Running EMR Core...")
    rebuild_edi_matchresults_core()
    print("[PSC] ✔ EMR Core complete.")

    print("\n[PSC] Step 2 — Resolving work day → bank day...")
    workday, bank_day = resolve_work_and_bank_day()

    print(f"[PSC] Work day: {workday}")
    print(f"[PSC] Bank day: {bank_day}")

    if not bank_day:
        print("[PSC] Cannot continue — no bank day.")
        return

    print("\n[PSC] Step 3 — Building posting screen (this will auto‑capture PSC)...")
    show_items_for_workday(workday)

    print("\n[PSC] ✔ PSC Core complete — PostingScreenCapture updated.")


if __name__ == "__main__":
    run_psc_core()
