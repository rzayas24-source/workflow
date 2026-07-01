#!/usr/bin/env python3

import os
from db import get_conn
from system_PSC_EDI_only_builder import build_psc_edi_only

# ⭐ HTML EOB folder
HTML_EOB_FOLDER = r"C:\Renfrew\2.AVATAR\1_HTML-EOB"


def file_contains_check(full_path, chk):
    try:
        with open(full_path, "r", errors="ignore") as file:
            contents = file.read()

            if chk in contents:
                return True
            if f"TRN*1*{chk}" in contents:
                return True
            if "BPR*" in contents and chk in contents:
                return True

            return False
    except:
        return False


def determine_proposed_name(chk):
    """
    No sequence numbers.
    Pure check-based naming:
    835-<check>.html
    """
    return f"835-{chk}.html"


def queue_proposed_html_changes():
    # STEP 1 — Rebuild PSC_EDI_only
    build_psc_edi_only()

    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }
    cur = conn.cursor()

    # STEP 2 — Load today's check numbers
    edi_rows = cur.execute("""
        SELECT edi_check
        FROM PSC_EDI_only
        ORDER BY edi_check
    """).fetchall()

    checks_to_process = [
        str(r["edi_check"]).strip()
        for r in edi_rows
        if r["edi_check"]
    ]

    # STEP 3 — Load ALL HTML files
    html_files = os.listdir(HTML_EOB_FOLDER)

    results = []

    # STEP 4 — Match files and propose names
    for chk in checks_to_process:
        matching_files = []

        for f in html_files:
            full_path = os.path.join(HTML_EOB_FOLDER, f)

            if file_contains_check(full_path, chk):
                matching_files.append(f)

        if not matching_files:
            results.append((chk, None, None, "NO FILE FOUND"))
            continue

        proposed = determine_proposed_name(chk)

        # ⭐ Reuse proposed_edi table
        cur.execute("""
            INSERT INTO proposed_edi (check_number, proposed_name)
            VALUES (?, ?)
            ON CONFLICT(check_number)
            DO UPDATE SET proposed_name = excluded.proposed_name,
                          created_at = datetime('now');
        """, (chk, proposed))

        results.append((chk, matching_files, proposed, "QUEUED"))

    conn.commit()
    conn.close()

    # STEP 5 — Print comparison
    print("\n==============================")
    print(" PROPOSED HTML EOB NAME CHANGES")
    print("==============================\n")

    for chk, current, proposed, status in results:
        print(f"Check#: {chk}")
        print(f"Current Files: {current}")
        print(f"Proposed:     {proposed}")
        print(f"Status:       {status}")
        print("------------------------------")

    print("\n✔ Proposed HTML EOB changes queued.\n")


if __name__ == "__main__":
    queue_proposed_html_changes()
