import sqlite3
from tabulate import tabulate

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def view_edi():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        rows = cur.execute("SELECT * FROM EDI").fetchall()
    except Exception as e:
        print(f"\nError: {e}\n")
        input("Press ENTER to exit...")
        return

    if not rows:
        print("\n>>> No EDI records found.\n")
        input("Press ENTER to exit...")
        return

    headers = rows[0].keys()

    print("\n=== EDI TABLE ===\n")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()

    input("Press ENTER to exit...")
