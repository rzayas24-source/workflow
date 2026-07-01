#!/usr/bin/env python3

import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def clear_balsheet():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n=== CLEAR BALSHEET TABLE ===\n")

    confirm = input("Are you sure you want to delete ALL rows? (y/n): ").strip().lower()
    if confirm != "y":
        print("\n>>> Cancelled. No rows deleted.\n")
        conn.close()
        return

    cur.execute("DELETE FROM Balsheet;")
    conn.commit()
    conn.close()

    print("\n>>> Balsheet table cleared successfully.\n")

if __name__ == "__main__":
    clear_balsheet()
