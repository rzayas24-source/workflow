📘 Lockbox Loading***
file: Lockbox-Load.py
Overview
This script automates the loading of Lockbox Excel files into the main Lockbox table inside the workflow database. It performs staging, validation, duplicate prevention, loading, archiving, and diagnostics in one run.

The script is designed to be run manually whenever a new Lockbox file is available.

Workflow Summary
Find the Lockbox file

Looks in: \\ren-fs01\users\rzayas\Downloads

Must start with: SearchResults

Must be an .xls file

Load into staging (LockboxLoad)

Clears the staging table

Reads the Excel file

Loads all rows into LockboxLoad

Duplicate Check

Compares "Check Number" in LockboxLoad against the main Lockbox table

If any duplicates exist:

Load is rejected

File is NOT archived

Diagnostics are printed

Load into final table (Lockbox)

If no duplicates are found

All rows from staging are inserted into Lockbox

Clear staging

LockboxLoad is emptied after a successful load

Archive the file

File is moved to: C:\Renfrew\Workflow\Archive

Diagnostics

Shows rows inserted

Shows final row counts

Confirms success or failure

Pauses so you can read the output

File Locations
Database:  
C:\Renfrew\Workflow\database.db

Incoming files:  
\\ren-fs01\users\rzayas\Downloads

Archive:  
C:\Renfrew\Workflow\Archive

What This Script Prevents
Duplicate check numbers entering the system

Accidental overwriting of data

Loading empty or malformed files

Losing the original file (only archived after success)

How to Run
Place the SearchResults*.xls file in your Downloads folder

Run the script

Read the diagnostics

Press ENTER to close the window

Notes
Only .xls files are supported

The script uses absolute paths, so it works from any folder

If the staging table is empty, the load is cancelled

If duplicates exist, the load is cancelled and the file stays in Downloads


📘 EDI Loader Module — Protected Version*****
file Balsheet-Entry-Bulk.py

Staging‑Safe, Duplicate‑Protected TRN Loader for Renfrew Workflow
📌 Overview
The EDI Loader Module — Protected Version is a controlled ingestion tool designed to safely load converted TRN‑style .txt files into the EDI table inside the Renfrew Workflow database.

This loader is built for data integrity, duplicate prevention, and safe archiving.
It ensures that no TRN file is ever archived unless it contributes at least one new check number.

The module is intended for daily or bulk ingestion of TRN‑converted EDI files.

🚀 Key Features
✔ Accepts all .txt files
Any file ending in .txt inside the TRN folder is processed.

✔ Parses converted TRN‑style structure
The loader expects:

Code
Line 1: Filename (ignored)
Line 2: Header (ignored)
Line 3+: check_date check_number check_amount
Malformed lines are skipped with warnings.

✔ Duplicate check_number protection
Before inserting any row, the loader checks:

sql
SELECT 1 FROM EDI WHERE check_number = ?
If the check number already exists:

It is not inserted

It is listed under duplicate rows

✔ File‑level acceptance logic
A file is accepted only if it contains at least one new check_number.

If a file contains only duplicates, it is:

Rejected

Not archived

Fully reported to the user

✔ Conditional archiving
Files are moved to the archive folder only if new rows were inserted.

This prevents losing files that need review.

✔ Full diagnostics
At the end of the run, the loader prints:

Total files scanned

Total .txt files processed

Number of rows inserted this run

Total rows in the EDI table

First 10 rows in EDI

Last 10 rows in EDI

✔ Pause at the end
The script pauses with:

Code
Press ENTER to exit...
This ensures the operator can review diagnostics before the window closes.

📂 Folder Structure
Code
C:\Renfrew\2.AVATAR\3_TRN_Bulk_Check\
    ├── *.txt                ← Incoming TRN files
    ├── Loaded\              ← Archive folder (only for accepted files)
🗄 Database Structure
The loader ensures the EDI table exists with:

sql
id            INTEGER PRIMARY KEY
check_date    TEXT
check_number  TEXT
check_amount  REAL
filename      TEXT
🔄 Processing Flow
1. Scan TRN folder
Every .txt file is discovered and evaluated.

2. Parse file
Extracts rows of:

Code
check_date, check_number, check_amount
3. Duplicate detection
Each check_number is checked against the database.

4. File acceptance decision
If no new rows → file rejected

If some new rows → file accepted

5. Insert new rows
Only new check_numbers are inserted.

6. Archive file (conditional)
File is moved to the archive folder only if new rows were inserted.

7. Diagnostics printed
Summary + first/last 10 rows.

🛡 Why This Version Is “Protected”
This loader prevents:

Accidental overwriting

Duplicate check_number insertion

Loss of files that contain only duplicates

Silent failures

Archiving files that didn’t load anything

Corrupt or malformed TRN rows entering the system

It is designed for safe, repeatable ingestion in a production environment.

🧪 Example Output
Code
>>> FILE ACCEPTED — 12 NEW ROWS FOUND.
>>> DUPLICATES FOUND (these were skipped):
      - 826149000008673
      - 826149000082248
Moved to archive: C:\Renfrew\...\Loaded\TRN_20260608.txt
--------------------------------------------------
Or for a rejected file:

Code
>>> FILE REJECTED — NO NEW ROWS FOUND: TRN_20260608.txt
>>> DUPLICATE CHECK NUMBERS IN THIS FILE:
      - 826149000008673
      - 826149000082248
>>> FILE NOT MOVED. PLEASE REVIEW.
🧭 When to Use This Loader
Use this module when:

Loading daily TRN‑converted EDI files

Bulk‑loading historical TRN files

Validating incoming EDI data

Ensuring no duplicate check_numbers enter the system

🧹 Safe to Clear
Clearing the EDI table is safe as long as you understand:

The loader will rebuild it from TRN files

Archived files will not reload unless moved back manually

📌 Auto‑Run Behavior
At the bottom:

python
if __name__ == "__main__":
    load_all_trn_files()
This means:

Double‑clicking the script runs the loader immediately

No additional setup is required

if feature is ran, and you must clear up group posting entry to start again, you must clear PostingScreenCapture and Balsheet Tables. Please consider the feature is always checking PostingScreenCapture check number vs Balsheet.
