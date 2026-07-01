#!/usr/bin/env python3

import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def view_calendar():
    conn = get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT bank_day, paperwork_day, weekday, is_weekend, is_closed, closure_reason
        FROM calendar
        ORDER BY bank_day
    """).fetchall()

    conn.close()

    print("\n==============================")
    print("         CALENDAR VIEW")
    print("==============================\n")

    print(f"{'BANK DAY':<12} {'PAPERWORK':<12} {'WEEKDAY':<10} {'WEEKEND':<8} {'CLOSED':<8} REASON")
    print("-" * 80)

    for bank_day, paperwork_day, weekday, is_weekend, is_closed, reason in rows:
        weekend = "YES" if is_weekend else "NO"
        closed = "YES" if is_closed else "NO"
        reason = reason if reason else ""
        print(f"{bank_day:<12} {paperwork_day:<12} {weekday:<10} {weekend:<8} {closed:<8} {reason}")

    print("\nTotal rows:", len(rows))
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    view_calendar()
