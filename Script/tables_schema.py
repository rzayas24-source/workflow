#!/usr/bin/env python3

from db import get_conn   # ⭐ unified DB engine
import os

def show_schema():
    print("\n==============================")
    print("        DATABASE SCHEMA")
    print("==============================")

    conn = get_conn()
    cur = conn.cursor()

    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cur.fetchall()]

    if not tables:
        print("\nNo tables found in database.")
        conn.close()
        os.system("pause")
        return

    print("\nTables found:")
    for t in tables:
        print(f"  • {t}")

    print("\n==============================")
    print("        TABLE DETAILS")
    print("==============================")

    for t in tables:
        print(f"\n--- {t} ---")

        # Row count
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            count = cur.fetchone()[0]
            print(f"Row count: {count}")
        except:
            print("Row count: ERROR")

        # Columns
        try:
            cur.execute(f"PRAGMA table_info({t})")
            cols = cur.fetchall()

            print("Columns:")
            for col in cols:
                cid, name, ctype, notnull, default, pk = col
                print(f"  - {name} ({ctype}){' [PK]' if pk else ''}")
        except Exception as e:
            print(f"Error reading columns: {e}")

    conn.close()

    print("\n==============================")
    print("Schema output complete.")
    print("==============================")

    os.system("pause")


if __name__ == "__main__":
    try:
        show_schema()
    except Exception as e:
        print("\nFATAL ERROR:")
        print(e)
        os.system("pause")
