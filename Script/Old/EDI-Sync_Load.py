import os
import sqlite3
from EDI_Loader import parse_trn_file   # adjust if needed

DB_PATH = r"C:\Renfrew\Workflow\database.db"
TARGET_FOLDER = r"C:\Renfrew\2.AVATAR\3_TRN_Bulk_Check\Converted_trn_to_txt"

print(">>> Sync-IN Started")
print(f">>> Scanning folder: {TARGET_FOLDER}")
print("--------------------------------------------------")

# Connect to DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get filenames already in DB
db_files = {row["filename"] for row in cur.execute("SELECT filename FROM EDI").fetchall()}

# Get TXT files in folder
folder_files = [f for f in os.listdir(TARGET_FOLDER) if f.lower().endswith(".txt")]

# Determine which files are new
new_files = [f for f in folder_files if f not in db_files]

print(">>> Diagnostics")
print(f"Files in folder: {len(folder_files)}")
print(f"Files already in DB: {len(db_files)}")
print(f"New files to load: {len(new_files)}")
print("--------------------------------------------------")

if new_files:
    print("New files detected:")
    for f in new_files:
        print("  -", f)
else:
    print("No new files found.")

print("--------------------------------------------------")
confirm = input("Proceed with loading these files? (y/n): ").strip().lower()

if confirm != "y":
    print(">>> Sync-IN cancelled by user.")
    input("Press ENTER to exit...")
    exit()

loaded = 0

for filename in new_files:
    full_path = os.path.join(TARGET_FOLDER, filename)
    print(f"Loading: {filename}")

    rows = parse_trn_file(full_path)

    for r in rows:
        cur.execute("""
            INSERT INTO EDI (check_date, check_number, check_amount, filename)
            VALUES (?, ?, ?, ?)
        """, (r[0], r[1], r[2], filename))

    loaded += 1

conn.commit()
conn.close()

print("--------------------------------------------------")
print(f"Files loaded: {loaded}")
print(">>> Sync-IN complete")
input("Press ENTER to exit...")
