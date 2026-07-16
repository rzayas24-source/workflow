import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

DB_PATH = r"C:\Renfrew\Workflow\database.db"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    return sqlite3.connect(DB_PATH)


# ------------------------------------------------------------
# GET FIRST PENDING IMPORTED FILE
# ------------------------------------------------------------
@app.get("/attachments/pending")
def get_first_pending():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, snapshot_path, review_status
        FROM imported_files
        WHERE review_status = 'Pending'
        ORDER BY id ASC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False
    }


@app.get("/queue")
def get_queue():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, snapshot_path, review_status
        FROM imported_files
        WHERE review_status = 'Pending'
        ORDER BY id ASC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "snapshot": row[2],
            "status": row[3],
        }
        for row in rows
    ]


def _pending_day_label(value):
    if not value:
        return "Unknown"

    text = str(value).strip()
    if not text:
        return "Unknown"

    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text[:19], fmt) if fmt.endswith("%H:%M:%S") and len(text) >= 19 else datetime.strptime(text[:10], fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

    if "T" in text:
        try:
            return datetime.fromisoformat(text.replace("Z", "")).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return text[:10] if len(text) >= 10 else text


@app.get("/pending/by-day")
def get_pending_by_day():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, processed_at
        FROM imported_files
        WHERE review_status = 'Pending'
        ORDER BY id ASC
    """)

    grouped = {}
    for row in cur.fetchall():
        day = _pending_day_label(row[2])
        grouped.setdefault(day, []).append({
            "id": row[0],
            "filename": row[1],
        })

    conn.close()
    return grouped


@app.get("/approved")
def get_approved():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, site, detail, amount, processed_at
        FROM imported_files
        WHERE review_status = 'Approved'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "site": row[2],
            "detail": row[3],
            "total": row[4] or 0,
            "date": row[5],
        }
        for row in rows
    ]


@app.get("/rejectlist")
def get_rejectlist():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, review_notes, processed_at
        FROM imported_files
        WHERE review_status = 'Rejected'
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "reason": row[2],
            "date": row[3],
        }
        for row in rows
    ]


# ------------------------------------------------------------
# NEXT PENDING FILE
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/next")
def get_next(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, snapshot_path, review_status
        FROM imported_files
        WHERE review_status = 'Pending' AND id > ?
        ORDER BY id ASC
        LIMIT 1
    """, (attachment_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False
    }


# ------------------------------------------------------------
# PREVIOUS PENDING FILE
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/prev")
def get_prev(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, snapshot_path, review_status
        FROM imported_files
        WHERE review_status = 'Pending' AND id < ?
        ORDER BY id DESC
        LIMIT 1
    """, (attachment_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return {"done": True}

    return {
        "id": row[0],
        "filename": row[1],
        "snapshot": row[2],
        "status": row[3],
        "done": False
    }


# ------------------------------------------------------------
# SNAPSHOT IMAGE
# ------------------------------------------------------------
@app.get("/attachments/{attachment_id}/snapshot")
def get_snapshot(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT snapshot_path FROM imported_files WHERE id = ?", (attachment_id,))
    row = cur.fetchone()
    conn.close()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    snapshot_path = row[0]

    if not os.path.exists(snapshot_path):
        raise HTTPException(status_code=404, detail="Snapshot file missing")

    return FileResponse(snapshot_path)


# ------------------------------------------------------------
# APPROVE FILE
# ------------------------------------------------------------
@app.post("/attachments/{attachment_id}/approve")
def approve_attachment(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE imported_files
        SET review_status = 'Approved'
        WHERE id = ?
    """, (attachment_id,))

    conn.commit()
    conn.close()

    return {"status": "approved", "id": attachment_id}


@app.post("/queue/{attachment_id}/approve")
def approve_queue_item(attachment_id: int):
    return approve_attachment(attachment_id)


# ------------------------------------------------------------
# REJECT FILE
# ------------------------------------------------------------
@app.post("/attachments/{attachment_id}/reject")
def reject_attachment(attachment_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE imported_files
        SET review_status = 'Rejected'
        WHERE id = ?
    """, (attachment_id,))

    conn.commit()
    conn.close()

    return {"status": "rejected", "id": attachment_id}


@app.post("/queue/{attachment_id}/reject")
def reject_queue_item(attachment_id: int):
    return reject_attachment(attachment_id)


# ------------------------------------------------------------
# RESET ALL TO PENDING
# ------------------------------------------------------------
@app.post("/reset")
def reset_all():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE imported_files
        SET review_status = 'Pending'
    """)

    conn.commit()
    conn.close()

    return {"status": "reset_all"}


# ------------------------------------------------------------
# RESET NEWEST DAY (IF YOU USE DATES)
# ------------------------------------------------------------
@app.post("/reset/newest-day")
def reset_newest_day():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT MAX(as_of_date) FROM imported_files")
    newest = cur.fetchone()[0]

    if newest:
        cur.execute("""
            UPDATE imported_files
            SET review_status = 'Pending'
            WHERE as_of_date = ?
        """, (newest,))
        conn.commit()

    conn.close()
    return {"status": "reset_newest_day", "date": newest}
from sites_api import router as sites_router
app.include_router(sites_router)
