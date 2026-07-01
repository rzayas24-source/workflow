#!/usr/bin/env python3

from db import get_conn
from system_calendar_core import get_current_work_day, normalize_mmddyyyy

def build_psc_edi_only():
    """
    Build PSC_EDI_only from PostingScreenCapture.
    Filters PSC down to only EDI-MATCH rows.
    """

    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    # 1. Get current work day
    workday = get_current_work_day()
    if not workday:
        print("[PSC_EDI] No current work day set.")
        conn.close()
        return

    # 2. Convert paperwork day → bank day
    row = cur.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (workday,)
    ).fetchone()

    if not row:
        print(f"[PSC_EDI] No calendar entry for paperwork day {workday}")
        conn.close()
        return

    bank_day_norm = normalize_mmddyyyy(row["bank_day"]) or row["bank_day"]

    # 3. Clear PSC_EDI_only
    cur.execute("DELETE FROM PSC_EDI_only")

    # 4. Pull EDI-MATCH rows from PSC
    psc_rows = cur.execute("""
        SELECT check_number,
               edi_amount,
               lockbox_amount,
               eft_amount,
               file_number
        FROM PostingScreenCapture
        WHERE date = ?
          AND source_type = 'EDI-MATCH'
    """, (bank_day_norm,)).fetchall()

    # 5. Insert into PSC_EDI_only
    for r in psc_rows:
        chk = str(r["check_number"]).strip()

        cur.execute("""
            INSERT INTO PSC_EDI_only (
                edi_check,
                edi_amount,
                lockbox_amount,
                eft_amount,
                match_date,
                created_at,
                filename
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
        """, (
            chk,
            r["edi_amount"],
            r["lockbox_amount"],
            r["eft_amount"],
            bank_day_norm,
            r["file_number"]
        ))

    conn.commit()
    conn.close()

    print(f"[PSC_EDI] ✔ PSC_EDI_only built for bank day {bank_day_norm}")


def run_psc_edi_core():
    """
    Build PSC_EDI_only AFTER PSC Core has already built PSC.
    """
    build_psc_edi_only()


if __name__ == "__main__":
    run_psc_edi_core()
