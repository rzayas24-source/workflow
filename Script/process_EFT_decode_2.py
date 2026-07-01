#!/usr/bin/env python3

import os
import pandas as pd

FOLDER = r"C:\Renfrew\Workflow"
INPUT_FILE = os.path.join(FOLDER, "output1.csv")
OUTPUT_FILE = os.path.join(FOLDER, "output2.csv")

# Load CSV
df = pd.read_csv(INPUT_FILE, dtype=str)

# Ensure column 22 exists
if df.shape[1] <= 22:
    raise Exception("output1.csv does not have at least 23 columns (index 22 missing).")

col22 = df.columns[22]

# ---------------------------------------------------
# col23: from col22, find *1* from the RIGHT
# delete everything to the LEFT including *1*
# ---------------------------------------------------
def make_col23(val):
    if pd.isna(val):
        return ""
    idx = val.rfind("*1*")
    if idx == -1:
        return ""
    return val[idx + len("*1*"):]

df["col23"] = df[col22].apply(make_col23)

# ---------------------------------------------------
# col24: from col23, find first *
# delete everything to the RIGHT including *
# FORCE col24 to TEXT
# ---------------------------------------------------
def make_col24(val):
    if pd.isna(val):
        return ""
    idx = val.find("*")
    if idx == -1:
        return val
    return val[:idx]

df["col24"] = df["col23"].apply(make_col24).astype(str)

# ---------------------------------------------------
# col25: from col22, find TRN*1*
# delete everything to the RIGHT including TRN*1*
# ---------------------------------------------------
def make_col25(val):
    if pd.isna(val):
        return ""
    idx = val.find("TRN*1*")
    if idx == -1:
        return val
    return val[:idx]

df["col25"] = df[col22].apply(make_col25)

# ---------------------------------------------------
# FORCE column index 51 to TEXT
# ---------------------------------------------------
if df.shape[1] > 51:
    col51 = df.columns[51]
    df[col51] = df[col51].astype(str)
else:
    print("Warning: Column index 51 does not exist in output1.csv")

# Save output
df.to_csv(OUTPUT_FILE, index=False)

print(f"Created {OUTPUT_FILE}")
