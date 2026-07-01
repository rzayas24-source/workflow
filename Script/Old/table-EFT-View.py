import sqlite3
from tabulate import tabulate

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def view_edi():
    print("\n>>> Checking EDI table...\n")

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Database error: {e}")
        input("Press ENTER to exit...")
        return

    try:
        rows = cur.execute("SELECT * FROM EDI").fetchall()
    except Exception as e:
        print(f"Query error: {e}")
        input("Press ENTER to exit...")
        return

    # If empty
    if not rows:
        print(">>> No EDI records found.\n")
        input("Press ENTER to exit...")
        return

    # If rows exist
    headers = rows[0].keys()
    print("=== EDI TABLE ===\n")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()

    input("Press ENTER to exit...")
