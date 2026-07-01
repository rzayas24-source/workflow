import os
import re
from tabulate import tabulate
from db import get_conn   # ⭐ dynamic DB connection


# -----------------------------
# COLUMN NORMALIZATION
# -----------------------------
def normalize_column_name(col):
    col = col.lower()
    col = re.sub(r"[ -]+", "_", col)
    if col[0].isdigit():
        col = "_" + col
    if col in ("from", "to"):
        col = col + "_"
    return col


def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    rows = cur.fetchall()

    raw_cols = [row[1] for row in rows]
    types = {row[1]: row[2].upper() for row in rows}  # raw_name → TYPE

    normalized_map = {normalize_column_name(c): c for c in raw_cols}
    return raw_cols, normalized_map, types


# -----------------------------
# DATABASE HELPERS
# -----------------------------
def list_tables(conn):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    return [row[0] for row in cur.fetchall()]


def clear_table(conn, table):
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table};")
    conn.commit()


def fetch_rows(conn, table, limit=None, sort_col=None):
    cur = conn.cursor()
    query = f"SELECT rowid, * FROM {table}"

    if sort_col:
        query += f' ORDER BY "{sort_col}"'

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)
    return cur.fetchall()


def delete_row(conn, table, rowid):
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE rowid = ?", (rowid,))
    conn.commit()


def pause():
    input("\nPress ENTER to continue...")


# -----------------------------
# REAL‑ONLY NUMBER FORMATTING
# -----------------------------
def format_real(v):
    if v is None:
        return v
    try:
        num = float(v)
        return f"{num:,.2f}"
    except:
        return v


# -----------------------------
# MAIN PROGRAM
# -----------------------------
def main():
    conn = get_conn()   # ⭐ use shared DB engine

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("=== TABLE LIST ===\n")

        tables = list_tables(conn)
        if not tables:
            print("No tables found.")
            pause()
            break

        for i, t in enumerate(tables, 1):
            print(f"{i}. {t}")

        choice = input("\nSelect table number (or 'q' to quit): ").strip()
        if choice.lower() == "q":
            break

        if not choice.isdigit() or not (1 <= int(choice) <= len(tables)):
            continue

        table = tables[int(choice) - 1]

        # Get columns + types
        raw_cols, colmap, types = get_columns(conn, table)

        os.system("cls" if os.name == "nt" else "clear")
        print(f"=== {table} ===")
        print("Columns (normalized → raw):")
        for norm, raw in colmap.items():
            print(f" - {norm}  (raw: {raw}, type: {types[raw]})")

        action = input("\nPress ENTER to enter table, or 'x' to clear table: ").strip().lower()

        if action == "x":
            confirm = input("Type 'confirm' to continue: ").strip().lower()
            if confirm == "confirm":
                confirm2 = input("Type 'clear' to permanently clear table: ").strip().lower()
                if confirm2 == "clear":
                    clear_table(conn, table)
                    print(f"\nTable '{table}' cleared.")
                    pause()
                    continue

        # Enter table view
        os.system("cls" if os.name == "nt" else "clear")
        print(f"=== Viewing {table} ===")

        limit_choice = input("View (1) Top 50 or (2) Full table: ").strip()
        limit = 50 if limit_choice == "1" else None

        print("\nColumns:")
        norm_keys = list(colmap.keys())
        for i, norm in enumerate(norm_keys, 1):
            print(f"{i}. {norm}")

        sort_choice = input("\nSort by column number (or ENTER for none): ").strip()
        sort_col = None

        if sort_choice.isdigit() and 1 <= int(sort_choice) <= len(norm_keys):
            selected_norm = norm_keys[int(sort_choice) - 1]
            sort_col = colmap[selected_norm]  # raw name

        rows = fetch_rows(conn, table, limit=limit, sort_col=sort_col)

        os.system("cls" if os.name == "nt" else "clear")
        print(f"=== {table} (showing {len(rows)} rows) ===\n")

        # Build table for tabulate WITH REAL‑ONLY FORMATTING
        display_cols = ["rowid"] + raw_cols

        table_data = []
        for row in rows:
            formatted_row = []
            for col_name, value in zip(display_cols, row):
                raw_col = col_name if col_name != "rowid" else None
                if raw_col and raw_col in types and types[raw_col] == "REAL":
                    formatted_row.append(format_real(value))
                else:
                    formatted_row.append(value)
            table_data.append(formatted_row)

        print(tabulate(table_data, headers=display_cols, tablefmt="grid"))

        delete_choice = input("\nDelete a row? Enter rowid or press ENTER to skip: ").strip()
        if delete_choice.isdigit():
            delete_row(conn, table, int(delete_choice))
            print(f"Row {delete_choice} deleted.")
            pause()

    conn.close()


if __name__ == "__main__":
    main()
