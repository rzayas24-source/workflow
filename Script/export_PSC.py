#!/usr/bin/env python3

import os
import xlsxwriter
import subprocess

from db import get_conn

EXPORT_FOLDER = r"C:\Renfrew\Workflow\DB_Exports"


def run_emr_core():
    subprocess.run(["python", "system_EMR_core.py"], check=True)


def run_psc_core():
    subprocess.run(["python", "system_PSC_core.py"], check=True)


def export_all_psc():
    conn = get_conn()
    conn.row_factory = lambda cursor, row: {
        cursor.description[i][0]: row[i] for i in range(len(row))
    }

    # Pull ALL PSC rows exactly as they exist
    rows = conn.execute("""
        SELECT
            id,
            check_number,
            source_type,
            payer_name,
            amount,
            date,
            file_number,
            edi_match,
            edi_amount,
            lockbox_amount,
            eft_amount,
            bank_day
        FROM PostingScreenCapture
        ORDER BY id
    """).fetchall()

    conn.close()

    if not rows:
        print("PSC table is empty. Nothing to export.")
        return

    os.makedirs(EXPORT_FOLDER, exist_ok=True)

    out_path = os.path.join(EXPORT_FOLDER, "PSC_Export.xlsx")

    workbook = xlsxwriter.Workbook(out_path)
    ws = workbook.add_worksheet("PSC")

    headers = [
        "ID",
        "CheckNumber",
        "SourceType",
        "PayerName",
        "Amount",
        "Date",
        "FileNumber",
        "EDI_Match",
        "EDI_Amount",
        "Lockbox_Amount",
        "EFT_Amount",
        "BankDay"
    ]

    # Write headers
    for col, h in enumerate(headers):
        ws.write(0, col, h)

    # Write PSC rows
    for r_index, row in enumerate(rows, start=1):
        ws.write(r_index, 0, row["id"])
        ws.write(r_index, 1, row["check_number"])
        ws.write(r_index, 2, row["source_type"])
        ws.write(r_index, 3, row["payer_name"])
        ws.write(r_index, 4, row["amount"])
        ws.write(r_index, 5, row["date"])
        ws.write(r_index, 6, row["file_number"])
        ws.write(r_index, 7, row["edi_match"])
        ws.write(r_index, 8, row["edi_amount"])
        ws.write(r_index, 9, row["lockbox_amount"])
        ws.write(r_index, 10, row["eft_amount"])
        ws.write(r_index, 11, row["bank_day"])

    workbook.close()

    print(f"\nExport complete:\n{out_path}\n")


if __name__ == "__main__":
    # Step 1: Build EMR
    run_emr_core()

    # Step 2: Build PSC
    run_psc_core()

    # Step 3: Export PSC
    export_all_psc()
