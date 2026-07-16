#!/usr/bin/env python3

from db import get_conn
from process_EDI_upload_part3 import stage_ediload_rows


def _ensure_edivett_schema(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS EDIvett (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_date TEXT,
            check_number TEXT,
            check_amount REAL,
            filename TEXT,
            transnum TEXT,
            batchnum TEXT,
            status TEXT,
            timestamp TEXT
        )
        """
    )

    existing = {row[1] for row in cur.execute("PRAGMA table_info(EDIvett)").fetchall()}
    for column in ("transnum", "batchnum", "status", "timestamp"):
        if column not in existing:
            cur.execute(f'ALTER TABLE EDIvett ADD COLUMN "{column}" TEXT')


def prepare_edi_vetting() -> dict[str, object]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        _ensure_edivett_schema(cur)
        stage_rows = cur.execute(
            """
            SELECT check_date, check_number, check_amount, filename, transnum, batchnum, status, timestamp
            FROM EDIstage
            ORDER BY id
            """
        ).fetchall()
        authority_checks = cur.execute(
            """
            SELECT check_number
            FROM EDI
            WHERE check_number IS NOT NULL AND check_number != ''
            """
        ).fetchall()
        authority_check_set = {
            str(row["check_number"]).strip()
            for row in authority_checks
            if str(row["check_number"]).strip()
        }

        cur.execute("DELETE FROM EDIvett")

        vetted_rows = []
        duplicate_checks = []
        batchnums = sorted(
            {
                str(row["batchnum"]).strip()
                for row in stage_rows
                if str(row["batchnum"]).strip()
            }
        )

        for row in stage_rows:
            check_number = str(row["check_number"] or "").strip()
            duplicate = check_number in authority_check_set if check_number else False
            if duplicate:
                duplicate_checks.append(check_number)

            vetted_rows.append(
                (
                    row["check_date"],
                    row["check_number"],
                    row["check_amount"],
                    row["filename"],
                    row["transnum"],
                    row["batchnum"],
                    "DUPLICATE" if duplicate else "Awaiting Import",
                    row["timestamp"],
                )
            )

        cur.executemany(
            """
            INSERT INTO EDIvett (
                check_date,
                check_number,
                check_amount,
                filename,
                transnum,
                batchnum,
                status,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            vetted_rows,
        )
        conn.commit()

        duplicate_checks = sorted({chk for chk in duplicate_checks if chk})
        duplicate_set = set(duplicate_checks)
        accepted_rows = sum(
            1
            for row in vetted_rows
            if str(row[1] or "").strip() not in duplicate_set
        )
        can_import = len(duplicate_checks) == 0
        if can_import:
            message = "Ready to confirm import into EDI."
        else:
            message = "Duplicate checks found. You can accept non-duplicates or redo the batch."
        return {
            "vetted_rows": len(vetted_rows),
            "accepted_rows": accepted_rows,
            "duplicate_checks": duplicate_checks,
            "duplicate_rows": duplicate_checks,
            "batchnum": ", ".join(batchnums) if batchnums else None,
            "can_import": can_import,
            "message": message,
        }
    finally:
        conn.close()


def confirm_edi_import(accept_non_duplicates: bool = False) -> dict[str, object]:
    prepared = prepare_edi_vetting()
    if not prepared["can_import"] and not accept_non_duplicates:
        return prepared

    conn = get_conn()
    cur = conn.cursor()
    try:
        vetted_rows = cur.execute(
            """
            SELECT check_date, check_number, check_amount, filename, transnum, batchnum, status, timestamp
            FROM EDIvett
            ORDER BY id
            """
        ).fetchall()
        if not vetted_rows:
            raise RuntimeError("No vetted EDI rows were found to import.")

        accepted_rows = [
            row
            for row in vetted_rows
            if not accept_non_duplicates or str(row["status"] or "").strip().upper() != "DUPLICATE"
        ]
        skipped_duplicates = len(vetted_rows) - len(accepted_rows)
        if not accepted_rows:
            return {
                "imported_rows": 0,
                "skipped_duplicates": skipped_duplicates,
                "can_import": False,
                "message": "No non-duplicate rows were available to import.",
            }

        cur.executemany(
            """
            INSERT INTO EDI (
                check_date,
                check_number,
                check_amount,
                filename,
                transnum,
                batchnum,
                status,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["check_date"],
                    row["check_number"],
                    row["check_amount"],
                    row["filename"],
                    row["transnum"],
                    row["batchnum"],
                    "Imported",
                    row["timestamp"],
                )
                for row in accepted_rows
            ],
        )

        cur.execute("DELETE FROM EDIstage")
        cur.execute("DELETE FROM EDIvett")
        conn.commit()
        return {
            "imported_rows": len(accepted_rows),
            "skipped_duplicates": skipped_duplicates,
            "accepted_non_duplicates": accept_non_duplicates,
            "message": (
                f"Imported {len(accepted_rows)} vetted row(s) into EDI."
                if not accept_non_duplicates
                else f"Imported {len(accepted_rows)} non-duplicate row(s) into EDI and skipped {skipped_duplicates} duplicate row(s)."
            ),
            "can_import": True,
        }
    finally:
        conn.close()


def reset_edi_work_tables() -> dict[str, object]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        deleted_load = cur.execute("DELETE FROM EDILoad").rowcount
        deleted_stage = cur.execute("DELETE FROM EDIstage").rowcount
        deleted_vett = cur.execute("DELETE FROM EDIvett").rowcount
        conn.commit()
        return {
            "message": "Cleared EDILoad, EDIstage, and EDIvett.",
            "deleted_load": deleted_load,
            "deleted_stage": deleted_stage,
            "deleted_vett": deleted_vett,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    print(stage_ediload_rows())
    print(prepare_edi_vetting())
