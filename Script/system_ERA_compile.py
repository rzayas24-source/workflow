#!/usr/bin/env python3

import os
from db import get_conn
from system_calendar_core import get_current_work_day, normalize_mmddyyyy

ERA_FOLDER = r"C:\Renfrew\2.AVATAR\2_ERA-835"


# ============================================================
# Resolve work day → bank day
# ============================================================

def resolve_bank_day():
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    workday = get_current_work_day()
    if not workday:
        print("[COMPILE] ERROR: No current work day set.")
        conn.close()
        return None, None

    row = cur.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (workday,)
    ).fetchone()

    conn.close()

    if not row:
        print(f"[COMPILE] ERROR: No calendar entry for paperwork day {workday}")
        return workday, None

    bank_day = normalize_mmddyyyy(row["bank_day"]) or row["bank_day"]
    return workday, bank_day


# ============================================================
# Pull PSC_EDI_only rows
# ============================================================

def pull_psceo_rows(bank_day):
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT edi_check,
               filename,
               lockbox_amount,
               eft_amount,
               edi_amount
        FROM PSC_EDI_only
        WHERE match_date = ?
        ORDER BY edi_check
    """, (bank_day,)).fetchall()

    conn.close()
    return rows


# ============================================================
# Check file contents for check number
# ============================================================

def file_contains_check(full_path, chk):
    try:
        with open(full_path, "r", errors="ignore") as f:
            return chk in f.read()
    except:
        return False


# ============================================================
# Build proposed_edi
# ============================================================

def build_proposed_edi(bank_day, psceo_rows):
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    print(f"\n[COMPILE] Clearing existing proposed_edi rows for bank day {bank_day}...")
    cur.execute("DELETE FROM proposed_edi WHERE bank_day = ?", (bank_day,))

    queued = []
    seq = 0

    # ERA folder contents
    if not os.path.exists(ERA_FOLDER):
        print("[COMPILE] ERROR: ERA folder does not exist:", ERA_FOLDER)
        return []

    era_files = sorted(os.listdir(ERA_FOLDER))

    # Search ERA files for each check number
    for r in psceo_rows:
        chk = str(r["edi_check"]).strip()

        print(f"\n[COMPILE] 🔎 Searching ERA files for check {chk}")

        for f in era_files:
            full_path = os.path.join(ERA_FOLDER, f)

            if file_contains_check(full_path, chk):
                proposed_name = f"{seq}-{chk}"
                seq += 1

                queued.append((chk, proposed_name))

                # FINAL — ONLY 4 columns
                cur.execute("""
                    INSERT INTO proposed_edi (
                        check_number,
                        proposed_name,
                        created_at,
                        bank_day
                    )
                    VALUES (?, ?, datetime('now'), ?)
                """, (chk, proposed_name, bank_day))

                print(f"      ✔ MATCH FOUND in file: {f}")
                print(f"      → Proposed name: {proposed_name}")

    conn.commit()
    conn.close()

    return queued


# ============================================================
# Main compiler utility
# ============================================================

def run_era_compile():

    workday, bank_day = resolve_bank_day()

    print("\n[COMPILE] 📅 Work day:", workday)
    print("[COMPILE] 🏦 Bank day:", bank_day)

    if not bank_day:
        print("[COMPILE] Cannot continue — no bank day.")
        return

    psceo_rows = pull_psceo_rows(bank_day)

    print(f"\n[COMPILE] 🔍 PSC_EDI_only rows for {bank_day}: {len(psceo_rows)}")
    if not psceo_rows:
        print("[COMPILE] No PSC_EDI_only rows found — nothing to compile.")
        return

    queued = build_proposed_edi(bank_day, psceo_rows)

    print("\n[COMPILE] 📦 Queue to rename:")
    for chk, name in queued:
        print(f"   • Check {chk} → {name}")

    print(f"\n[COMPILE] ✔ Compile complete — {len(queued)} items queued.")


if __name__ == "__main__":
    run_era_compile()
