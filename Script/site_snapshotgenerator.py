#!/usr/bin/env python3

import os
from pdf2image import convert_from_path
from db import get_conn   # ⭐ dynamic DB connection

# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

PDF_FOLDER = r"C:\Renfrew\1.COPY - Copy\3._SITES"
SNAPSHOT_FOLDER = r"C:\Renfrew\Workflow\snapshots"
POPPLER_PATH = r"C:\poppler\Library\bin"

os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)

# ---------------------------------------------------------
# Generate a snapshot from the first page of a PDF
# ---------------------------------------------------------
def generate_snapshot(pdf_path, out_path):
    pages = convert_from_path(
        pdf_path,
        dpi=150,
        first_page=1,
        last_page=1,
        poppler_path=POPPLER_PATH
    )
    pages[0].save(out_path, "PNG")
    return out_path

# ---------------------------------------------------------
# Ensure DB row exists for this PDF
# ---------------------------------------------------------
def ensure_db_row(cur, filename):
    cur.execute("SELECT id FROM imported_files WHERE filename = ?", (filename,))
    row = cur.fetchone()

    if row:
        return row[0]

    cur.execute("""
        INSERT INTO imported_files (filename, review_status)
        VALUES (?, 'Pending')
    """, (filename,))
    return cur.lastrowid

# ---------------------------------------------------------
# Process PDFs in the folder (folder-driven)
# ---------------------------------------------------------
def process_folder_pdfs():
    conn = get_conn()
    cur = conn.cursor()

    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("No PDFs found in the folder.")
        conn.close()
        return

    total = len(pdf_files)
    print(f"\nFound {total} PDF(s) in folder.\n")

    for index, filename in enumerate(pdf_files, start=1):
        print(f"[{index}/{total}] Processing {filename}")

        pdf_path = os.path.join(PDF_FOLDER, filename)

        # Ensure DB row exists
        file_id = ensure_db_row(cur, filename)

        # Snapshot path (correct folder)
        snapshot_path = os.path.join(SNAPSHOT_FOLDER, f"{file_id}.png")

        # Skip if snapshot already exists
        if os.path.exists(snapshot_path):
            print(f"   ✔ Snapshot already exists: {snapshot_path}")
            continue

        try:
            print("   Generating snapshot...")
            generate_snapshot(pdf_path, snapshot_path)

            cur.execute("""
                UPDATE imported_files
                SET snapshot_path = ?, review_status = 'Pending'
                WHERE id = ?
            """, (snapshot_path, file_id))

            print(f"   ✔ Snapshot saved: {snapshot_path}")

        except Exception as e:
            print(f"❌ Error generating snapshot for {filename}: {e}")

    conn.commit()
    conn.close()
    print("\nAll folder-based snapshot processing complete.")

# ---------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------
if __name__ == "__main__":
    process_folder_pdfs()
