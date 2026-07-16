#!/usr/bin/env python3

import os
import shutil
from datetime import datetime

from db import get_conn
from system_paths import TRN_FOLDER, TRN_LOADED_FOLDER


def _normalize_mmddyyyy(s):
    if not s:
        return None
    s = str(s).strip()
    if "/" in s and len(s) == 10:
        return s
    if len(s) == 8 and s.isdigit():
        yyyy = s[0:4]
        mm = s[4:6]
        dd = s[6:8]
        return f"{mm}/{dd}/{yyyy}"
    for f in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, f).strftime("%m/%d/%Y")
        except ValueError:
            pass
    return s


def _parse_trn_file(path):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]

    if len(lines) < 3:
        return rows

    for line in lines[2:]:
        parts = line.split()
        if len(parts) < 3:
            continue

        check_date = _normalize_mmddyyyy(parts[0])
        check_number = parts[1]
        try:
            check_amount = float(parts[2])
        except ValueError:
            continue

        rows.append((check_date, check_number, check_amount))

    return rows


def _ensure_ediload_schema(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS EDILoad (
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

    existing = {row[1] for row in cur.execute("PRAGMA table_info(EDILoad)").fetchall()}
    for column in ("transnum", "batchnum", "status", "timestamp"):
        if column not in existing:
            cur.execute(f'ALTER TABLE EDILoad ADD COLUMN "{column}" TEXT')


def list_queued_trn_files():
    if not os.path.exists(TRN_FOLDER):
        return []

    return sorted(
        filename
        for filename in os.listdir(TRN_FOLDER)
        if filename.lower().endswith(".trn") and os.path.isfile(os.path.join(TRN_FOLDER, filename))
    )


def _unique_loaded_path(filename: str) -> str:
    base_name = os.path.basename(filename)
    stem, ext = os.path.splitext(base_name)
    candidate = os.path.join(TRN_LOADED_FOLDER, base_name)
    counter = 2

    while os.path.exists(candidate):
        candidate = os.path.join(TRN_LOADED_FOLDER, f"{stem}_{counter}{ext}")
        counter += 1

    return candidate


def load_trn_queue_to_ediload():
    if not os.path.exists(TRN_FOLDER):
        return {
            "file_count": 0,
            "loaded_files": [],
            "skipped_files": [],
            "row_count": 0,
            "duplicate_rows": [],
            "batchnum": None,
            "first_transnum": None,
            "last_transnum": None,
            "timestamp": None,
        }

    os.makedirs(TRN_LOADED_FOLDER, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()
    loaded_files: list[str] = []
    skipped_files: list[str] = []
    duplicate_rows: list[str] = []
    row_count = 0
    file_count = 0

    try:
        _ensure_ediload_schema(cur)

        work_row = cur.execute(
            "SELECT transnum_count, batchnum_count FROM work_state WHERE id = 1"
        ).fetchone()
        if not work_row:
            raise RuntimeError("work_state row 1 not found")

        current_transnum = int(work_row["transnum_count"] or 0)
        current_batchnum = int(work_row["batchnum_count"] or 0)
        next_batchnum = current_batchnum + 1
        load_timestamp = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        next_transnum = current_transnum + 1
        last_transnum = current_transnum

        for filename in list_queued_trn_files():
            file_count += 1
            full_path = os.path.join(TRN_FOLDER, filename)
            rows = _parse_trn_file(full_path)
            if not rows:
                skipped_files.append(filename)
                continue

            new_rows = []
            for check_date, check_number, amount in rows:
                exists = cur.execute(
                    "SELECT 1 FROM EDILoad WHERE check_number = ?",
                    (check_number,),
                ).fetchone()
                if exists:
                    duplicate_rows.append(check_number)
                    continue
                new_rows.append((check_date, check_number, amount))

            if not new_rows:
                skipped_files.append(filename)
                continue

            for check_date, check_number, amount in new_rows:
                cur.execute(
                    """
                    INSERT INTO EDILoad (
                        check_date,
                        check_number,
                        check_amount,
                        filename,
                        transnum,
                        batchnum,
                        status,
                        timestamp
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        check_date,
                        check_number,
                        amount,
                        filename,
                        str(next_transnum),
                        str(next_batchnum),
                        "Loaded",
                        load_timestamp,
                    ),
                )
                row_count += 1
                last_transnum = next_transnum
                next_transnum += 1

            conn.commit()
            shutil.move(full_path, _unique_loaded_path(filename))
            loaded_files.append(filename)

        if row_count > 0:
            cur.execute(
                """
                UPDATE work_state
                SET transnum_count = ?,
                    batchnum_count = ?
                WHERE id = 1
                """,
                (last_transnum, next_batchnum),
            )
            conn.commit()
    finally:
        conn.close()

    return {
        "file_count": file_count,
        "loaded_files": loaded_files,
        "skipped_files": skipped_files,
        "row_count": row_count,
        "duplicate_rows": sorted(dict.fromkeys(duplicate_rows)),
        "batchnum": next_batchnum if row_count > 0 else None,
        "first_transnum": current_transnum + 1 if row_count > 0 else None,
        "last_transnum": last_transnum if row_count > 0 else None,
        "timestamp": load_timestamp if row_count > 0 else None,
    }


if __name__ == "__main__":
    result = load_trn_queue_to_ediload()
    print(result)
