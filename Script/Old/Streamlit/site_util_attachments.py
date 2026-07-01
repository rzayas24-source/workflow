import os
from db import get_conn

def get_attachment_by_offset(current_id, direction):
    conn = get_conn()
    cur = conn.cursor()

    if direction == "next":
        cur.execute("""
            SELECT id, filename, moved_to, snapshot_path
            FROM imported_files
            WHERE id > ?
              AND review_status='Pending'
              AND snapshot_path IS NOT NULL
              AND snapshot_path <> ''
            ORDER BY id ASC LIMIT 1
        """, (current_id,))
    else:
        cur.execute("""
            SELECT id, filename, moved_to, snapshot_path
            FROM imported_files
            WHERE id < ?
              AND review_status='Pending'
              AND snapshot_path IS NOT NULL
              AND snapshot_path <> ''
            ORDER BY id DESC LIMIT 1
        """, (current_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    if not os.path.exists(row[3]):
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "saved_path": row[2],
        "snapshot_path": row[3]
    }

def get_first_pending():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, moved_to, snapshot_path
        FROM imported_files
        WHERE review_status='Pending'
          AND snapshot_path IS NOT NULL
          AND snapshot_path <> ''
        ORDER BY id ASC LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "saved_path": row[2],
        "snapshot_path": row[3]
    }
