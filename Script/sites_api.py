from fastapi import APIRouter, HTTPException
import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

router = APIRouter()

def get_conn():
    return sqlite3.connect(DB_PATH)


@router.get("/sites")
def get_sites():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, name, description, active FROM sites ORDER BY name;")
    rows = cur.fetchall()

    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "description": r[2],
            "active": r[3]
        }
        for r in rows
    ]


@router.post("/sites")
def add_site(site: dict):
    name = site.get("name")
    description = site.get("description", "")

    if not name:
        raise HTTPException(status_code=400, detail="Site name is required")

    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO sites (name, description, active) VALUES (?, ?, 1);",
            (name, description)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Site already exists")

    conn.close()
    return {"status": "ok", "message": "Site added"}


@router.put("/sites/{site_id}")
def update_site(site_id: int, site: dict):
    name = site.get("name")
    description = site.get("description")
    active = site.get("active")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM sites WHERE id = ?;", (site_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Site not found")

    cur.execute(
        "UPDATE sites SET name = ?, description = ?, active = ? WHERE id = ?;",
        (name, description, active, site_id)
    )

    conn.commit()
    conn.close()

    return {"status": "ok", "message": "Site updated"}


@router.delete("/sites/{site_id}")
def delete_site(site_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM sites WHERE id = ?;", (site_id,))
    if not cur.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Site not found")

    cur.execute("DELETE FROM sites WHERE id = ?;", (site_id,))
    conn.commit()
    conn.close()

    return {"status": "ok", "message": "Site deleted"}
