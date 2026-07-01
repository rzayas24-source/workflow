import os
import sqlite3
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
