import os
import sqlite3

# Paths
DB_PATH = r"C:\Renfrew\Workflow\database.db"
TARGET_FOLDER = r"C:\Renfrew\2.AVATAR\3_TRN_Bulk_Check\Converted_trn_to_txt"

print(">>> EDI Database Sync Started")
print(f">>> Checking folder: {TARGET_FOLDER}")
print("--------------------------------------------------")

# Connect to DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all rows
rows = cur.execute("SELECT id, filename FROM EDI").fetchall()

deleted = 0
kept = 0

for row in rows:
    file_path = os.path.join(TARGET_FOLDER, row["filename"])

    # If file is missing → delete DB row
    if not os.path.exists(file_path):
        print(f"Deleting DB row for missing file: {row['filename']}")
        cur.execute("DELETE FROM EDI WHERE id = ?", (row["id"],))
        deleted += 1
    else:
        kept += 1

conn.commit()
conn.close()

print("--------------------------------------------------")
print(f"DB rows deleted (file missing): {deleted}")
print(f"DB rows kept (file exists):     {kept}")
print(">>> Sync complete")
input("Press ENTER to exit...")
