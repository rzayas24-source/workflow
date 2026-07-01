"""
system_calendar_core.py
Pure calendar + work‑day logic module.

Contains:
- DB setup
- Date normalization
- Calendar CRUD
- Work‑day helpers
- Status + range display

Does NOT contain:
- Posting logic
- EDI logic
- CLI
"""

from db import get_conn   # ⭐ unified DB engine
from datetime import datetime, timedelta
import traceback


# ============================================================
#   DB INITIALIZATION
# ============================================================

def init_db():
    conn = get_conn()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS calendar (
            id INTEGER PRIMARY KEY,
            bank_day TEXT UNIQUE,
            weekday TEXT,
            is_weekend INTEGER,
            is_closed INTEGER,
            closure_reason TEXT,
            paperwork_day TEXT
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS work_state (
            id INTEGER PRIMARY KEY,
            current_work_day TEXT
        );
    """)

    row = conn.execute("SELECT id FROM work_state WHERE id = 1").fetchone()
    if not row:
        conn.execute("INSERT INTO work_state (id, current_work_day) VALUES (1, NULL)")

    conn.commit()
    conn.close()


# ============================================================
#   DATE HELPERS
# ============================================================

def normalize_mmddyyyy(s):
    if not s:
        return None

    s = str(s).strip()
    s = s.replace(".", "/").replace("\\", "/").replace(",", "").strip()

    fmts = [
        "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y",
        "%Y/%m/%d", "%Y-%m-%d", "%Y%m%d",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
        "%m%d%Y", "%m%d%y",
    ]

    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.strftime("%m/%d/%Y")
        except:
            pass

    try:
        dt = datetime.fromisoformat(s)
        return dt.strftime("%m/%d/%Y")
    except:
        pass

    digits = "".join([c for c in s if c.isdigit()])
    if len(digits) == 8:
        for fmt in ("%Y%m%d", "%m%d%Y"):
            try:
                dt = datetime.strptime(digits, fmt)
                return dt.strftime("%m/%d/%Y")
            except:
                pass

    tokens = [
        t for t in s.replace("T", " ").replace(":", " ")
        .replace("-", " ").replace("/", " ").split()
        if any(c.isdigit() for c in t)
    ]

    if len(tokens) >= 3:
        p = ["".join([c for c in x if c.isdigit()]) for x in tokens[:3]]
        try:
            if len(p[0]) == 4:
                dt = datetime(int(p[0]), int(p[1]), int(p[2]))
            else:
                dt = datetime(int(p[2]), int(p[0]), int(p[1]))
            return dt.strftime("%m/%d/%Y")
        except:
            pass

    return None


def to_date(s):
    return datetime.strptime(s, "%m/%d/%Y")


def from_date(d):
    return d.strftime("%m/%d/%Y")


def get_day_info(d):
    wd = d.weekday()
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][wd]
    return weekday, 1 if wd >= 5 else 0


def next_weekday(d):
    wd = d.weekday()
    if wd in [0, 1, 2, 3]:
        return d + timedelta(days=1)
    if wd == 4:
        return d + timedelta(days=3)
    if wd == 5:
        return d + timedelta(days=2)
    return d + timedelta(days=1)


def next_open_paperwork_day(conn, start_date):
    d = next_weekday(start_date)
    while True:
        row = conn.execute(
            "SELECT is_closed FROM calendar WHERE bank_day = ?",
            (from_date(d),)
        ).fetchone()

        if row is None or row[0] == 0:
            return d

        d = next_weekday(d)


# ============================================================
#   CURRENT WORK DAY
# ============================================================

def get_current_work_day():
    conn = get_conn()
    row = conn.execute(
        "SELECT current_work_day FROM work_state WHERE id = 1"
    ).fetchone()
    conn.close()

    if row and row[0]:
        return row[0]

    return None


def set_current_work_day(date_str):
    conn = get_conn()
    init_db()
    conn.execute(
        "UPDATE work_state SET current_work_day = ? WHERE id = 1",
        (date_str,)
    )
    conn.commit()
    conn.close()
    print(f"Current work day set to: {date_str}")


def advance_current_work_day():
    current = get_current_work_day()
    if not current:
        print("No current work day is set.")
        return

    conn = get_conn()
    init_db()

    rows = conn.execute("""
        SELECT paperwork_day, is_closed
        FROM calendar
        WHERE paperwork_day > ?
        ORDER BY paperwork_day ASC
    """, (current,)).fetchall()

    next_day = None
    for r in rows:
        if r[1] == 0:
            next_day = r[0]
            break

    if not next_day:
        print(f"Current work day {current} completed. No further open days found.")
        conn.close()
        return

    conn.execute(
        "UPDATE work_state SET current_work_day = ? WHERE id = 1",
        (next_day,)
    )
    conn.commit()
    conn.close()

    print(f"Current work day {current} completed. New current work day: {next_day}")


# ============================================================
#   CALENDAR CORE OPS
# ============================================================

def get_last_bank_day(conn):
    row = conn.execute(
        "SELECT bank_day FROM calendar ORDER BY bank_day DESC LIMIT 1"
    ).fetchone()
    return to_date(row[0]) if row else None


def add_days(n):
    conn = get_conn()
    init_db()

    last = get_last_bank_day(conn)
    if last is None:
        last = datetime.today() - timedelta(days=1)

    current = last + timedelta(days=1)

    for _ in range(n):
        weekday, is_weekend = get_day_info(current)
        is_closed = is_weekend
        closure_reason = "Weekend" if is_weekend else ""
        paperwork = next_open_paperwork_day(conn, current)

        conn.execute("""
            INSERT OR IGNORE INTO calendar
            (bank_day, weekday, is_weekend, is_closed, closure_reason, paperwork_day)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            from_date(current),
            weekday,
            is_weekend,
            is_closed,
            closure_reason,
            from_date(paperwork)
        ))

        current += timedelta(days=1)

    conn.commit()
    conn.close()
    print(f"Added {n} day(s).")


def close_day(date_str, reason):
    conn = get_conn()
    init_db()
    conn.execute("""
        UPDATE calendar
        SET is_closed = 1, closure_reason = ?
        WHERE bank_day = ?
    """, (reason, date_str))
    conn.commit()
    conn.close()
    print(f"{date_str} marked closed: {reason}")


def open_day(date_str):
    conn = get_conn()
    init_db()
    conn.execute("""
        UPDATE calendar
        SET is_closed = 0, closure_reason = ''
        WHERE bank_day = ?
    """, (date_str,))
    conn.commit()
    conn.close()
    print(f"{date_str} reopened.")


def set_paperwork_day(bank_day_str, new_paperwork_str):
    conn = get_conn()
    init_db()
    conn.execute("""
        UPDATE calendar
        SET paperwork_day = ?
        WHERE bank_day = ?
    """, (new_paperwork_str, bank_day_str))
    conn.commit()
    conn.close()
    print(f"Paperwork day updated: {bank_day_str} → {new_paperwork_str}")


def set_bank_day(old_bank_str, new_bank_str):
    conn = get_conn()
    init_db()
    conn.execute("""
        UPDATE calendar
        SET bank_day = ?
        WHERE bank_day = ?
    """, (new_bank_str, old_bank_str))
    conn.commit()
    conn.close()
    print(f"Bank day changed: {old_bank_str} → {new_bank_str}")


def delete_all_days():
    conn = get_conn()
    init_db()
    conn.execute("DROP TABLE IF EXISTS calendar")
    conn.commit()
    conn.close()
    init_db()
    print("All calendar days deleted. Calendar table rebuilt empty.")


def setup(start_date_str):
    delete_all_days()
    conn = get_conn()
    init_db()

    d = to_date(start_date_str)
    weekday, is_weekend = get_day_info(d)

    conn.execute("""
        INSERT INTO calendar
        (bank_day, weekday, is_weekend, is_closed, closure_reason, paperwork_day)
        VALUES (?, ?, ?, 0, '', ?)
    """, (from_date(d), weekday, is_weekend, from_date(d)))

    conn.commit()
    conn.close()
    print(f"Setup complete. Anchor bank day: {from_date(d)} (OPEN).")


def delete_days(from_str, to_str):
    conn = get_conn()
    init_db()
    conn.execute("""
        DELETE FROM calendar
        WHERE bank_day BETWEEN ? AND ?
    """, (from_str, to_str))
    conn.commit()
    conn.close()
    print(f"Deleted days from {from_str} to {to_str} (inclusive).")


def build_from(start_date_str, n):
    setup(start_date_str)
    add_days(n)
    print(f"Build-from complete: start {start_date_str}, added {n} days.")


# ============================================================
#   STATUS + RANGE
# ============================================================

def show_status():
    conn = get_conn()
    init_db()

    today_str = datetime.today().strftime("%m/%d/%Y")

    today_row = conn.execute(
        "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
        (today_str,)
    ).fetchone()

    last_row = conn.execute(
        "SELECT bank_day FROM calendar ORDER BY bank_day DESC LIMIT 1"
    ).fetchone()

    print("----- STATUS -----")
    print(f"Today (system date): {today_str}")

    if today_row:
        print(f"Today's paperwork maps to bank day: {today_row[0]}")
    else:
        print("No calendar entry for today's paperwork day.")

    if last_row:
        print(f"Highest bank day created: {last_row[0]}")
    else:
        print("No bank days exist yet.")

    current_work = get_current_work_day()
    if current_work:
        row = conn.execute(
            "SELECT bank_day FROM calendar WHERE paperwork_day = ?",
            (current_work,)
        ).fetchone()
        bank_for_current = row[0] if row else "N/A"

        rows = conn.execute("""
            SELECT paperwork_day, is_closed
            FROM calendar
            WHERE paperwork_day > ?
            ORDER BY paperwork_day ASC
        """, (current_work,)).fetchall()

        next_open = None
        for r in rows:
            if r[1] == 0:
                next_open = r[0]
                break

        print(f"Current Work Day: {current_work}")
        print(f"Bank day for Current Work Day: {bank_for_current}")
        if next_open:
            print(f"Next Work Day (open): {next_open}")
        else:
            print("No further open work days found.")
    else:
        print("Current Work Day: (not set)")

    conn.close()


def show_calendar_range(start_str, end_str):
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    conn = get_conn()
    init_db()

    rows = conn.execute("""
        SELECT bank_day, weekday, is_closed, closure_reason, paperwork_day
        FROM calendar
        WHERE bank_day BETWEEN ? AND ?
        ORDER BY bank_day ASC
    """, (start_str, end_str)).fetchall()

    if not rows:
        print(f"No calendar entries between {start_str} and {end_str}")
        conn.close()
        return

    print(f"\n{CYAN}----- CALENDAR RANGE -----{RESET}")
    print(f"From: {start_str}   To: {end_str}\n")
    print("BANK DAY     WKD   CLOSED   PAPERWORK     REASON")
    print("--------------------------------------------------")

    current_work = get_current_work_day()

    for r in rows:
        bank_day = r[0]
        weekday = r[1]
        closed_txt = "YES" if r[2] else "No"
        reason = r[3] or ""
        paperwork = r[4]

        line = (
            f"{bank_day}   {weekday:<3}   {closed_txt:<5}   "
            f"{paperwork:<12} {reason:<15}"
        )

        if current_work and paperwork == current_work:
            print(f"{YELLOW}{line}   <-- CURRENT WORK DAY{RESET}")
        else:
            print(line)

    conn.close()
