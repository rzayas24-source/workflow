#!/usr/bin/env python3

import os
import glob
import shutil
import subprocess
import pandas as pd
from db import get_conn   # ⭐ dynamic DB connection

# ---------------------------------------------------
# PATHS
# ---------------------------------------------------
BASE = r"C:\Renfrew\Workflow"

SCRIPT_FOLDER = os.path.join(BASE, "Script")
OUTPUT3 = os.path.join(BASE, "output3.csv")
ARCHIVE = os.path.join(BASE, "Archive")
DOWNLOADS = r"\\ren-fs01\users\rzayas\Downloads"
HOLD = os.path.join(BASE, "Hold")

os.makedirs(ARCHIVE, exist_ok=True)
os.makedirs(HOLD, exist_ok=True)

# ---------------------------------------------------
# FUNCTION: GET OLDEST EFT FILE
# ---------------------------------------------------
def get_oldest_eft_file():
    eft_files = [
        f for f in os.listdir(BASE)
        if f.lower().startswith("dep_1101_tran")
    ]

    if not eft_files:
        return None

    eft_files = sorted(
        eft_files,
        key=lambda f: os.path.getmtime(os.path.join(BASE, f))
    )

    return eft_files[0]

# ---------------------------------------------------
# MAIN LOOP — PROCESS ONE FILE AT A TIME
# ---------------------------------------------------
while True:
    selected_file = get_oldest_eft_file()

    if not selected_file:
        print("\nNo EFT files left to process.")
        break

    print(f"\nProcessing EFT file (oldest): {selected_file}")

    selected_path = os.path.join(BASE, selected_file)

    # ---------------------------------------------------
    # TEMPORARILY MOVE OTHER EFT FILES TO HOLD
    # ---------------------------------------------------
    others = [
        f for f in os.listdir(BASE)
        if f.lower().startswith("dep_1101_tran") and f != selected_file
    ]

    for f in others:
        src = os.path.join(BASE, f)
        dest = os.path.join(HOLD, f)
        try:
            shutil.move(src, dest)
            print(f"Temporarily moved {src} → {dest}")
        except Exception as e:
            print(f"Could not move {src} to Hold: {e}")

    # ---------------------------------------------------
    # 1. RUN DECODER SCRIPTS
    # ---------------------------------------------------
    decoder_scripts = sorted(
        [
            f for f in os.listdir(SCRIPT_FOLDER)
            if f.lower().startswith("process_eft_decode_") and f.lower().endswith(".py")
        ],
        key=lambda x: int(x.split("_")[-1].split(".")[0])
    )

    if not decoder_scripts:
        print("❌ No decoder scripts found in Script folder.")
        raise SystemExit

    for script in decoder_scripts:
        script_path = os.path.join(SCRIPT_FOLDER, script)
        print(f"Running decoder: {script_path}")
        subprocess.run(["python", script_path], check=True)

    # ---------------------------------------------------
    # 2. LOAD output3.csv
    # ---------------------------------------------------
    print(f"Loading {OUTPUT3}...")
    df = pd.read_csv(OUTPUT3, dtype=str)

    required_cols = ["As-Of Date", "Credit Amt", "col24", "col25"]
    for col in required_cols:
        if col not in df.columns:
            raise Exception(f"Missing column in output3.csv: {col}")

    # ---------------------------------------------------
    # 3. LOAD INTO EFTload
    # ---------------------------------------------------
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS EFTload (
        Date TEXT,
        Amount REAL,
        CheckNumber TEXT,
        Payer TEXT
    );
    """)

    cur.execute("DELETE FROM EFTload;")

    rows = []
    for _, row in df.iterrows():
        date = row["As-Of Date"]
        amount = row["Credit Amt"]
        check_number = row["col24"]
        payer = row["col25"]

        try:
            amount_real = float(amount.replace(",", "")) if amount.strip() else None
        except:
            amount_real = None

        rows.append((date, amount_real, check_number, payer))

    cur.executemany(
        "INSERT INTO EFTload (Date, Amount, CheckNumber, Payer) VALUES (?, ?, ?, ?);",
        rows
    )

    conn.commit()
    print(f"Loaded {len(rows)} rows into EFTload.")

    # ---------------------------------------------------
    # 4. CHECK FOR DUPLICATE DATES
    # ---------------------------------------------------
    print("Checking for duplicate dates...")

    cur.execute("SELECT DISTINCT Date FROM EFTload;")
    eftload_dates = {row[0] for row in cur.fetchall()}

    cur.execute("SELECT DISTINCT Date FROM EFT;")
    eft_dates = {row[0] for row in cur.fetchall()}

    duplicates = eftload_dates.intersection(eft_dates)

    # ---------------------------------------------------
    # 4B. HANDLE REJECTION IF DUPLICATES FOUND
    # ---------------------------------------------------
    if duplicates:
        print("\n❌ ERROR: Cannot load EFT data.")
        for d in duplicates:
            print(f"Duplicate date detected: {d}")

        print("\nReturning file to Downloads...")

        try:
            src = selected_path
            dest = os.path.join(DOWNLOADS, selected_file)
            shutil.move(src, dest)
            print(f"Returned {src} → {dest}")
        except Exception as e:
            print(f"Could not return file: {e}")

        print("\nDeleting output files...")
        for path in glob.glob(os.path.join(BASE, "*output*")):
            try:
                os.remove(path)
                print(f"Deleted {path}")
            except Exception as e:
                print(f"Could not delete {path}: {e}")

        # Restore other EFT files
        for f in os.listdir(HOLD):
            src = os.path.join(HOLD, f)
            dest = os.path.join(BASE, f)
            try:
                shutil.move(src, dest)
                print(f"Restored {src} → {dest}")
            except Exception as e:
                print(f"Could not restore {src}: {e}")

        conn.close()
        raise SystemExit

    print("No duplicate dates found. Safe to load.")

    # ---------------------------------------------------
    # 5. APPEND EFTload → EFT
    # ---------------------------------------------------
    print("Appending EFTload into EFT...")

    cur.execute("""
    INSERT INTO EFT (Date, Amount, CheckNumber, Payer)
    SELECT Date, Amount, CheckNumber, Payer
    FROM EFTload;
    """)

    conn.commit()

    # ---------------------------------------------------
    # 6. CLEAR EFTload
    # ---------------------------------------------------
    cur.execute("DELETE FROM EFTload;")
    conn.commit()
    conn.close()

    print("EFTload successfully merged into EFT and cleared.")

    # ---------------------------------------------------
    # 7. DELETE ALL FILES WITH 'output' IN NAME
    # ---------------------------------------------------
    for path in glob.glob(os.path.join(BASE, "*output*")):
        try:
            os.remove(path)
            print(f"Deleted {path}")
        except Exception as e:
            print(f"Could not delete {path}: {e}")

    # ---------------------------------------------------
    # 8. MOVE PROCESSED FILE TO ARCHIVE
    # ---------------------------------------------------
    try:
        src = selected_path
        dest = os.path.join(ARCHIVE, selected_file)
        shutil.move(src, dest)
        print(f"Moved {src} → {dest}")
    except Exception as e:
        print(f"Could not move {src}: {e}")

    # ---------------------------------------------------
    # 9. RESTORE OTHER EFT FILES FROM HOLD
    # ---------------------------------------------------
    for f in os.listdir(HOLD):
        src = os.path.join(HOLD, f)
        dest = os.path.join(BASE, f)
        try:
            shutil.move(src, dest)
            print(f"Restored {src} → {dest}")
        except Exception as e:
            print(f"Could not restore {src}: {e}")

print("\nEFT pipeline complete.")
