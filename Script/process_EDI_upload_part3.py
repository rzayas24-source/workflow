#!/usr/bin/env python3

from db import get_conn


def _ensure_edistage_schema(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS EDIstage (
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

    existing = {row[1] for row in cur.execute("PRAGMA table_info(EDIstage)").fetchall()}
    for column in ("transnum", "batchnum", "status", "timestamp"):
        if column not in existing:
            cur.execute(f'ALTER TABLE EDIstage ADD COLUMN "{column}" TEXT')


def stage_ediload_rows() -> dict[str, object]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        _ensure_edistage_schema(cur)
        source_rows = cur.execute(
            """
            SELECT check_date, check_number, check_amount, filename, transnum, batchnum, status, timestamp
            FROM EDILoad
            ORDER BY id
            """
        ).fetchall()

        cur.execute("DELETE FROM EDIstage")
        if not source_rows:
            conn.commit()
            return {
                "staged_rows": 0,
                "batchnum": None,
                "first_transnum": None,
                "last_transnum": None,
                "message": "No EDILoad rows found to stage.",
            }

        staged_rows = []
        batchnums = sorted(
            {
                str(row["batchnum"]).strip()
                for row in source_rows
                if str(row["batchnum"]).strip()
            }
        )
        first_transnum = None
        last_transnum = None
        for row in source_rows:
            transnum = str(row["transnum"] or "").strip()
            batchnum = str(row["batchnum"] or "").strip()
            staged_rows.append(
                (
                    row["check_date"],
                    row["check_number"],
                    row["check_amount"],
                    row["filename"],
                    transnum,
                    batchnum,
                    "Staged",
                    row["timestamp"],
                )
            )
            if transnum:
                if first_transnum is None:
                    first_transnum = transnum
                last_transnum = transnum

        cur.executemany(
            """
            INSERT INTO EDIstage (
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
            staged_rows,
        )
        conn.commit()
        return {
            "staged_rows": len(staged_rows),
            "batchnum": ", ".join(batchnums) if batchnums else None,
            "first_transnum": first_transnum,
            "last_transnum": last_transnum,
            "message": f"Staged {len(staged_rows)} row(s) into EDIstage.",
        }
    finally:
        conn.close()


if __name__ == "__main__":
    print(stage_ediload_rows())
