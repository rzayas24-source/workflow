#!/usr/bin/env python3

import os
import pandas as pd
from datetime import datetime

FOLDER = r"C:\Renfrew\Workflow"
INPUT_FILE = os.path.join(FOLDER, "output2.csv")
OUTPUT_FILE = os.path.join(FOLDER, "output3.csv")

# ---------------------------------------------------
# DATE NORMALIZATION FUNCTION
# ---------------------------------------------------
def normalize_mmddyyyy(s):
    if not s:
        return ""
    s = str(s).strip()

    # Already MM/DD/YYYY
    if "/" in s and len(s) == 10:
        return s

    # YYYYMMDD
    if len(s) == 8 and s.isdigit():
        yyyy = s[0:4]
        mm = s[4:6]
        dd = s[6:8]
        return f"{mm}/{dd}/{yyyy}"

    # Try common formats
    fmts = ["%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y", "%m/%d/%y"]
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.strftime("%m/%d/%Y")
        except:
            pass

    return s  # fallback

# ---------------------------------------------------
# LOAD CSV
# ---------------------------------------------------
df = pd.read_csv(INPUT_FILE, dtype=str)

# ---------------------------------------------------
# REQUIRED COLUMNS
# A  = index 0   → As-Of Date
# N  = index 13  → Credit Amt
# AZ = index 51  → Check-Number
# BA = index 52  → Payers
# ---------------------------------------------------

required_indices = [0, 13, 51, 52]

if df.shape[1] <= max(required_indices):
    raise Exception("One or more required columns (A, N, AZ, BA) do not exist in output2.csv")

cols = df.columns
df_out = df[[cols[i] for i in required_indices]].copy()

df_out.columns = ["As-Of Date", "Credit Amt", "col24", "col25"]

# ---------------------------------------------------
# NORMALIZE DATE COLUMN
# ---------------------------------------------------
df_out["As-Of Date"] = df_out["As-Of Date"].apply(normalize_mmddyyyy)

# ---------------------------------------------------
# FORCE ALL COLUMNS TO TEXT
# ---------------------------------------------------
for col in df_out.columns:
    df_out[col] = df_out[col].astype(str)

# ---------------------------------------------------
# DATE VERIFICATION
# ---------------------------------------------------
bad_dates = df_out[~df_out["As-Of Date"].str.match(r"\d{2}/\d{2}/\d{4}")]

if not bad_dates.empty:
    print("\n⚠ WARNING: Non-normalized dates detected in output3.csv:")
    print(bad_dates)
else:
    print("\nAll dates normalized to MM/DD/YYYY.")

# ---------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------
df_out.to_csv(OUTPUT_FILE, index=False)
print(f"\nCreated {OUTPUT_FILE}")
