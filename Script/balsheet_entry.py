#!/usr/bin/env python3

from db import get_conn
from datetime import datetime

# ---------------------------------------------------------
# WORKDAY
# ---------------------------------------------------------

def get_current_workday():
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT current_work_day FROM work_state WHERE id = 1").fetchone()
    conn.close()

    if row and row[0]:
        return row[0]  # already normalized YYYY-MM-DD

    return datetime.now().strftime("%Y-%m-%d")

# ---------------------------------------------------------
# SAFE FLOAT
# ---------------------------------------------------------

def safe_float(v):
    if v is None:
        return None
    v = str(v).strip()
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        print("Invalid number, please enter a valid amount.")
        return safe_float(input("Amount: "))

# ---------------------------------------------------------
# YES/NO PROMPT
# ---------------------------------------------------------

def prompt_yes_no(message):
    while True:
        v = input(f"{message} (y/n): ").strip().lower()
        if v in ("y", "n"):
            return v
        print("Please enter 'y' or 'n'.")

# ---------------------------------------------------------
# UNIFIED ID GENERATOR (ControlsTools.GenID)
# ---------------------------------------------------------

def get_next_entry_id(posting_date):
    """
    Unified ID generator using ControlsTools.GenID.
    Always produces a globally unique ID.
    """
    date_key = posting_date.replace("-", "")  # YYYYMMDD

    conn = get_conn()
    cur = conn.cursor()

    # Read current GenID
    row = cur.execute("SELECT GenID FROM ControlsTools WHERE id = 1").fetchone()

    if row is None:
        current_seq = 0
        cur.execute("INSERT INTO ControlsTools (id, GenID) VALUES (1, 0)")
    else:
        current_seq = row[0]

    next_seq = current_seq + 1

    cur.execute("""
        UPDATE ControlsTools
        SET GenID = ?
        WHERE id = 1
    """, (next_seq,))

    conn.commit()
    conn.close()

    return f"{date_key}-{next_seq}"

# ---------------------------------------------------------
# MAIN ENTRY LOGIC
# ---------------------------------------------------------

def run_single_entry():
    print("\n=== BALSHEET DATA ENTRY ===")

    posting_date = get_current_workday()
    print(f"Posting Date: {posting_date}")

    entry_id = get_next_entry_id(posting_date)
    print(f"EntryID: {entry_id}\n")

    data = {}
    data["PostingDate"] = posting_date
    data["EntryID"] = entry_id

    # Amount
    amount = None
    while amount is None:
        amount = safe_float(input("Amount: "))
    data["Amount"] = amount

    # Type
    while True:
        t = input("Type (E-EFT, L-Lockbox, S-Site, F-Fix, O-Other): ").strip().upper()
        if t not in ("E", "L", "S", "F", "O"):
            print("Invalid type. Must be one of: E, L, S, F, O.")
            continue
        if t == "S":
            site = input("Enter 2-digit site code: ").strip()
            if len(site) == 2 and site.isdigit():
                data["Type"] = f"S-{site}"
                break
            else:
                print("Site code must be exactly 2 digits.")
                continue
        else:
            data["Type"] = t
            break

    # Payer
    data["Payer"] = input("Payer: ").strip()

    # Check Number
    data["Check Number"] = input("Check Number: ").strip()

    # EDI
    while True:
        edi = input("EDI (y/n): ").strip().lower()
        if edi not in ("y", "n"):
            print("EDI must be 'y' or 'n'.")
            continue
        data["EDI"] = "Y" if edi == "y" else "N"
        break

    # Poster
    if data["EDI"] == "Y":
        data["Poster"] = "R"
        print("EDI is Yes, Poster set to Raul (R).")
    else:
        poster = input("Poster (N=Nick, R=Raul) [default N]: ").strip().upper()
        if poster not in ("N", "R", ""):
            print("Invalid poster. Only N or R allowed. Defaulting to N.")
            poster = "N"
        if poster == "":
            poster = "N"
        data["Poster"] = poster
        if poster == "N":
            confirm = prompt_yes_no("Poster is Nick. Confirm?")
            if confirm == "n":
                while True:
                    poster = input("Poster (N=Nick, R=Raul): ").strip().upper()
                    if poster in ("N", "R"):
                        data["Poster"] = poster
                        break
                    print("Invalid poster. Only N or R allowed.")

    # EOB
    data["EOB"] = input("EOB (D=download, S=Scan, W=WF, N=None, 1-up=WF #): ").strip()

    # UnPosted
    unposted_flag = prompt_yes_no("Any amount unposted?")
    if unposted_flag == "n":
        unposted = 0.0
    else:
        full_flag = prompt_yes_no("Is it the full amount?")
        if full_flag == "y":
            unposted = amount
        else:
            unposted = None
            while unposted is None:
                unposted = safe_float(input("Enter unposted amount: "))
    data["UnPosted"] = unposted

    # Misc
    misc_flag = prompt_yes_no("Any Misc?")
    if misc_flag == "n":
        misc = None
        misc_type = ""
    else:
        misc = None
        while misc is None:
            misc = safe_float(input("Misc amount: "))
        misc_type = input("Misc type: ").strip()
    data["Misc"] = misc
    data["Misc-Type"] = misc_type

    # Notes
    data["Notes"] = input("Notes: ").strip()

    # Raul/Nick split
    misc_val = misc if misc is not None else 0.0
    base = amount - (unposted if unposted is not None else 0.0) - misc_val

    if data["Poster"] == "R":
        raul_amt = base
        nick_amt = 0.0
        print(f"Calculated Raul amount: {raul_amt:.2f}")
        confirm = prompt_yes_no("Confirm Raul amount?")
        if confirm == "n":
            raul_amt = None
            while raul_amt is None:
                raul_amt = safe_float(input("Enter Raul amount: "))
        data["Raul"] = raul_amt
        data["Nick"] = nick_amt
    else:
        nick_amt = base
        raul_amt = 0.0
        print(f"Calculated Nick amount: {nick_amt:.2f}")
        confirm = prompt_yes_no("Confirm Nick amount?")
        if confirm == "n":
            nick_amt = None
            while nick_amt is None:
                nick_amt = safe_float(input("Enter Nick amount: "))
        data["Nick"] = nick_amt
        data["Raul"] = raul_amt

    # Problems / Needs / From / To
    problems_flag = prompt_yes_no("Were there any problems?")
    if problems_flag == "n":
        data["Needs"] = ""
        data["To"] = ""
        data["From"] = ""
    else:
        needs = input("What problems occurred? ").strip()
        data["Needs"] = needs

        other_days_flag = prompt_yes_no("Were any other days involved?")
        to_val = ""
        from_val = ""
        if other_days_flag == "y":
            go_to_flag = prompt_yes_no("Did money go TO another day?")
            if go_to_flag == "y":
                to_val = input("Enter TO date (YYYY-MM-DD): ").strip()

            come_from_flag = prompt_yes_no("Did money come FROM another day?")
            if come_from_flag == "y":
                from_val = input("Enter FROM date (YYYY-MM-DD): ").strip()

        data["To"] = to_val
        data["From"] = from_val

    # Final verification
    print("\n=== VERIFY BALSHEET ENTRY ===\n")
    for key in [
        "EntryID","PostingDate","Type","Amount","Payer","Check Number","EDI",
        "Poster","EOB","UnPosted","Misc","Misc-Type","Notes","Nick","Raul",
        "Needs","From","To"
    ]:
        print(f"{key}: {data[key]}")
    print()

    final_confirm = prompt_yes_no("Confirm and finish entry sequence?")
    if final_confirm == "n":
        print("\n>>> Entry cancelled. Nothing posted.\n")
        return

    # Insert into DB
    conn = get_conn()
    conn.execute("""
        INSERT INTO Balsheet (
            EntryID, PostingDate, Type, Amount, Payer, "Check Number",
            EDI, Poster, EOB, UnPosted, Misc, "Misc-Type", Notes,
            Nick, Raul, Needs, "From", "To"
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["EntryID"], data["PostingDate"], data["Type"], data["Amount"],
        data["Payer"], data["Check Number"], data["EDI"], data["Poster"],
        data["EOB"], data["UnPosted"], data["Misc"], data["Misc-Type"],
        data["Notes"], data["Nick"], data["Raul"], data["Needs"],
        data["From"], data["To"]
    ))
    conn.commit()
    conn.close()

    print(f"\n>>> Entry {data['EntryID']} posted successfully.\n")

# ---------------------------------------------------------
# LOOP
# ---------------------------------------------------------

def balsheet_insert():
    while True:
        run_single_entry()
        again = input("Enter another? (y/n): ").strip().lower()
        if again != "y":
            print("\nExiting entry screen.\n")
            break

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":
    balsheet_insert()
