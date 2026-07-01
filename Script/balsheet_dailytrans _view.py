#!/usr/bin/env python3

from db import get_conn
from tabulate import tabulate

def get_real_columns():
    """Return REAL column names from Balsheet, normalized to lowercase."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(Balsheet);")
    real_cols = {row[1].lower() for row in cur.fetchall() if row[2].upper() == "REAL"}
    conn.close()
    return real_cols

def format_currency(value):
    """Format REAL values as #,###.00 and prepend non-breaking space."""
    try:
        num = float(value)
        return "\u00A0" + f"{num:,.2f}"
    except:
        return value

def view_balsheet():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            EntryID,
            PostingDate,
            Type,
            Amount,
            Payer,
            "Check Number",
            EDI,
            Poster,
            EOB,
            UnPosted,
            Misc,
            "Misc-Type",
            Notes,
            Nick,
            Raul,
            Needs,
            "From",
            "To"
        FROM Balsheet
        ORDER BY 
            PostingDate ASC,
            CAST(substr(EntryID, instr(EntryID, '-') + 1) AS INTEGER) ASC
    """)

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("\n>>> Balsheet is empty.\n")
        input("Press Enter to exit...")
        return

    headers = [
        "EntryID", "PostingDate", "Type", "Amount", "Payer", "Check Number",
        "EDI", "Poster", "EOB", "UnPosted", "Misc", "Misc-Type", "Notes",
        "Nick", "Raul", "Needs", "From", "To"
    ]

    real_cols = get_real_columns()

    formatted_rows = []
    for row in rows:
        new_row = []
        for header, value in zip(headers, row):
            if header.lower() in real_cols:
                new_row.append(format_currency(value))
            else:
                new_row.append("" if value is None else str(value))
        formatted_rows.append(new_row)

    colalign = ["right" if h.lower() in real_cols else "left" for h in headers]

    print("\n=== BALSHEET VIEW ===\n")
    print(tabulate(
        formatted_rows,
        headers=headers,
        tablefmt="grid",
        colalign=colalign
    ))
    print()

    print("Tip: Hold Ctrl and press + to zoom in, or Ctrl and - to zoom out.\n")

    input("Press Enter to exit...")

if __name__ == "__main__":
    view_balsheet()
