#!/usr/bin/env python3

import os
import pandas as pd

FOLDER = r"C:\Renfrew\Workflow"
KEYWORD = "dep_1101_tran"
OUTPUT_FILE = os.path.join(FOLDER, "output1.csv")

def process_dep_files():
    files = [f for f in os.listdir(FOLDER) if f.lower().startswith(KEYWORD)]

    if not files:
        print("No DEP_1101_TRAN files found.")
        return

    for f in files:
        path = os.path.join(FOLDER, f)
        print(f"Processing: {f}")

        # Load Excel or CSV automatically
        if f.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(path, dtype=str)
        else:
            df = pd.read_csv(path, dtype=str)

        # Ensure column 22 exists
        if df.shape[1] <= 22:
            print(f"File {f} does not have 23 columns. Skipping.")
            continue

        col22 = df.columns[22]

        # Filter rows containing TRN*1*
        filtered = df[df[col22].str.contains(r"TRN\*1\*", na=True)]

        # Save output
        filtered.to_csv(OUTPUT_FILE, index=False)
        print(f"Saved filtered results to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_dep_files()
