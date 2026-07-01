#!/usr/bin/env python3

import os
import shutil
from datetime import datetime

# ============================
# CONFIG
# ============================

SOURCE_FOLDER = r"\\ren-fs01\users\rzayas\Downloads"
DEST_FOLDER = r"C:\Renfrew\Workflow"

# Match EFT files
KEYWORD = "dep_1101_tran"

# ============================
# ENSURE DEST FOLDER EXISTS
# ============================

os.makedirs(DEST_FOLDER, exist_ok=True)

# ============================
# PROCESS EFT FILES
# ============================

files = os.listdir(SOURCE_FOLDER)
moved_files = []
skipped_files = []

for f in files:
    full_path = os.path.join(SOURCE_FOLDER, f)

    if not os.path.isfile(full_path):
        continue

    if f.lower().startswith(KEYWORD):
        src = full_path
        dst = os.path.join(DEST_FOLDER, f)

        try:
            shutil.move(src, dst)
            moved_files.append(f)
        except Exception as e:
            print(f"ERROR moving {f}: {e}")
    else:
        skipped_files.append(f)

# ============================
# DIAGNOSTICS
# ============================

print("\n==============================")
print("        EFT LOADER REPORT")
print("==============================")

print(f"\nSource folder: {SOURCE_FOLDER}")
print(f"Destination:   {DEST_FOLDER}")
print(f"Timestamp:     {datetime.now().isoformat()}")

print("\n--- SUMMARY ---")
print(f"Total files scanned: {len(files)}")
print(f"EFT files moved:     {len(moved_files)}")

print("\n--- MOVED FILES ---")
if moved_files:
    for f in moved_files:
        print(f"  ✔ {f}")
else:
    print("  (none)")

print("\n==============================")
print("Loader complete.")
print("==============================")

input("\nPress Enter to exit...")
