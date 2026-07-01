import sqlite3
from tabulate import tabulate

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def view_table(table_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        rows = cur.execute(f"SELECT * FROM {table_name}").fetchall()
    except Exception as e:
        print(f"\nError: {e}\n")
        input("Press ENTER to exit...")
        return

    if not rows:
        print(f"\n>>> {table_name} is empty.\n")
        input("Press ENTER to exit...")
        return

    headers = rows[0].keys()
    print(f"\n=== TABLE: {table_name} ===\n")
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()

    input("Press ENTER to exit...")

if __name__ == "__main__":
    # CHANGE THIS TO VIEW ANY TABLE
    view_table("PostingScreenCapture")

