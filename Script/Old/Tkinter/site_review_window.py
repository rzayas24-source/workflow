import tkinter as tk
from review_window import ReviewWindow  # your Tkinter class
import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def get_next_pending():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, filename, saved_path, snapshot_path
        FROM imported_files
        WHERE review_status='Pending'
        ORDER BY id ASC
        LIMIT 1
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

def start_review():
    attachment = get_next_pending()
    if not attachment:
        print("No pending items.")
        return

    root = tk.Tk()
    ReviewWindow(root, attachment)
    root.mainloop()

if __name__ == "__main__":
    start_review()
