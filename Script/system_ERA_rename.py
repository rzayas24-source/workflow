#!/usr/bin/env python3

import os
import shutil
from db import get_conn
from system_calendar_core import get_current_work_day, normalize_mmddyyyy

ERA_FOLDER = r"C:\Renfrew\2.AVATAR\2_ERA-835"
ERA_OUT_FOLDER = r"C:\Renfrew\2.AVATAR\2_ERA-835\RENAMED"


def resolve_bank_day():
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    workday = get_current_work_day()
    row = cur.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (workday,)
    ).fetchone()

    conn.close()

    if not row:
        print("[RENAME] ERROR: No calendar entry for paperwork day", workday)
        return workday, None

    bank_day = normalize_mmddyyyy(row["bank_day"]) or row["bank_day"]
    return workday, bank_day


def pull_proposed(bank_day):
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT check_number, proposed_name
        FROM proposed_edi
        WHERE bank_day = ?
        ORDER BY proposed_name
    """, (bank_day,)).fetchall()

    conn.close()
    return rows


def file_contains_check(full_path, chk):
    try:
        with open(full_path, "r", errors="ignore") as f:
            return chk in f.read()
    except:
        return False


def run_era_rename():

    workday, bank_day = resolve_bank_day()

    print("\n[RENAME] 📅 Work day:", workday)
    print("[RENAME] 🏦 Bank day:", bank_day)

    if not bank_day:
        print("[RENAME] Cannot continue — no bank day.")
        return

    proposed_rows = pull_proposed(bank_day)

    print(f"\n[RENAME] 🔍 Proposed rename rows: {len(proposed_rows)}")
    if not proposed_rows:
        print("[RENAME] Nothing to rename.")
        return

    if not os.path.exists(ERA_FOLDER):
        print("[RENAME] ERROR: ERA folder does not exist:", ERA_FOLDER)
        return

    era_files = sorted(os.listdir(ERA_FOLDER))
    os.makedirs(ERA_OUT_FOLDER, exist_ok=True)

    print("\n[RENAME] 🚚 Beginning rename operations...\n")

    renamed_count = 0

    for r in proposed_rows:
        chk = str(r["check_number"]).strip()
        new_name = r["proposed_name"]

        print(f"   🔎 Check {chk}")
        print(f"      Proposed: {new_name}")

        match_file = None

        # Search inside ERA files for the check number
        for f in era_files:
            full_path = os.path.join(ERA_FOLDER, f)
            if file_contains_check(full_path, chk):
                match_file = f
                break

        if not match_file:
            print(f"      ✖ No ERA file contains check {chk}")
            continue

        print(f"      ✔ Found ERA file: {match_file}")

        src_path = os.path.join(ERA_FOLDER, match_file)

        # ⭐ KEEP ORIGINAL EXTENSION
        orig_ext = os.path.splitext(match_file)[1]
        dst_path = os.path.join(ERA_OUT_FOLDER, new_name + orig_ext)

        try:
            shutil.move(src_path, dst_path)
            print(f"      ✔ Renamed → {new_name}{orig_ext}")
            renamed_count += 1
        except Exception as e:
            print(f"      ✖ ERROR renaming {match_file}: {e}")

    print(f"\n[RENAME] ✔ Rename complete — {renamed_count} files renamed.")


if __name__ == "__main__":
    run_era_rename()

