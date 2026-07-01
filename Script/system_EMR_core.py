"""
system_EMR_core.py
EDI_MatchResults rebuild engine.

Contains:
- EDI_MatchResults rebuild logic
- Normalization helpers (local)
- Shared utilities

Does NOT contain:
- Posting logic
- Calendar logic
- CLI
"""

from db import get_conn   # ⭐ dynamic DB connection
from datetime import datetime


# ============================================================
#   DATE NORMALIZATION
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
        except Exception:
            pass

    try:
        dt = datetime.fromisoformat(s)
        return dt.strftime("%m/%d/%Y")
    except Exception:
        pass

    digits = "".join([c for c in s if c.isdigit()])
    if len(digits) == 8:
        for fmt in ("%Y%m%d", "%m%d%Y"):
            try:
                dt = datetime.strptime(digits, fmt)
                return dt.strftime("%m/%d/%Y")
            except Exception:
                pass

    tokens = [t for t in s.replace("T", " ").replace(":", " ").replace("-", " ").replace("/", " ").split()
              if any(c.isdigit() for c in t)]
    if len(tokens) >= 3:
        p = ["".join([c for c in x if c.isdigit()]) for x in tokens[:3]]
        try:
            if len(p[0]) == 4:
                dt = datetime(int(p[0]), int(p[1]), int(p[2]))
            else:
                dt = datetime(int(p[2]), int(p[0]), int(p[1]))
            return dt.strftime("%m/%d/%Y")
        except Exception:
            pass

    return None


# ============================================================
#   CHECK NUMBER NORMALIZATION
# ============================================================

def normalize_checknum(v):
    """
    Normalize check numbers across EDI, Lockbox, EFT:
    - Strip spaces
    - Uppercase
    - Remove non-alphanumeric
    - DO NOT strip leading zeros (per Raul)
    """
    if not v:
        return ""
    v = str(v).strip().upper()
    return "".join(c for c in v if c.isalnum())


# ============================================================
#   EDI MATCHRESULTS REBUILD ENGINE
# ============================================================

def rebuild_edi_matchresults_core():
    """
    Rebuild EDI_MatchResults from EDI, Lockbox, EFT using strict matching.
    EFT date takes priority for match_date.
    """
    print("Rebuilding EDI_MatchResults...")

    conn = get_conn()
    conn.row_factory = lambda cursor, row: {cursor.description[i][0]: row[i] for i in range(len(row))}

    conn.execute("""
        CREATE TABLE IF NOT EXISTS EDI_MatchResults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edi_check TEXT,
            edi_amount REAL,
            lockbox_amount REAL,
            eft_amount REAL,
            match_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("DELETE FROM EDI_MatchResults;")

    # Load source tables
    edi_rows = conn.execute("""
        SELECT id, check_number, check_amount, check_date
        FROM EDI
    """).fetchall()

    lock_rows = conn.execute("""
        SELECT [Check Number] AS check_number,
               [Transaction Total] AS txn_total,
               [Deposit Date] AS deposit_date
        FROM Lockbox
    """).fetchall()

    eft_rows = conn.execute("""
        SELECT CheckNumber AS check_number,
               Amount AS amount,
               Date AS as_of_date
        FROM EFT
    """).fetchall()

    # Build lookup dictionaries
    lock_by_chk = {}
    for r in lock_rows:
        chk = normalize_checknum(r["check_number"])
        try:
            amt = float(str(r["txn_total"]).replace(",", "").strip()) if r["txn_total"] not in (None, "") else 0.0
        except Exception:
            amt = 0.0

        lock_by_chk.setdefault(chk, []).append({
            "amount": amt,
            "deposit_date": r["deposit_date"]
        })

    eft_by_chk = {}
    for r in eft_rows:
        chk = normalize_checknum(r["check_number"])
        try:
            amt = float(str(r["amount"]).replace(",", "").strip()) if r["amount"] not in (None, "") else 0.0
        except Exception:
            amt = 0.0

        eft_by_chk.setdefault(chk, []).append({
            "amount": amt,
            "as_of_date": r["as_of_date"]
        })

    # Build match results
    for e in edi_rows:
        edi_chk = normalize_checknum(e["check_number"])

        try:
            edi_amt = float(str(e["check_amount"]).replace(",", "").strip()) if e["check_amount"] not in (None, "") else 0.0
        except Exception:
            edi_amt = 0.0

        # LOCKBOX
        lock_amt = 0.0
        lock_date_norm = None
        if edi_chk in lock_by_chk:
            for lr in lock_by_chk[edi_chk]:
                lock_amt += lr["amount"]
                if not lock_date_norm:
                    lock_date_norm = normalize_mmddyyyy(lr["deposit_date"])

        # EFT
        eft_amt = 0.0
        eft_date_norm = None
        if edi_chk in eft_by_chk:
            for er in eft_by_chk[edi_chk]:
                eft_amt += er["amount"]
                if not eft_date_norm:
                    eft_date_norm = normalize_mmddyyyy(er["as_of_date"])

        # NEW RULE: EFT date → Lockbox date → EDI date
        raw_date = eft_date_norm or lock_date_norm or e["check_date"]
        match_date_norm = normalize_mmddyyyy(raw_date)

        conn.execute("""
            INSERT INTO EDI_MatchResults
            (edi_check, edi_amount, lockbox_amount, eft_amount, match_date)
            VALUES (?, ?, ?, ?, ?)
        """, (edi_chk, edi_amt, lock_amt, eft_amt, match_date_norm))

    conn.commit()
    conn.close()

    print("EDI_MatchResults rebuild complete.")
