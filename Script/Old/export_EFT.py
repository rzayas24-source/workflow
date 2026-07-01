#!/usr/bin/env python3

from db import get_conn
import os
import pandas as pd
from datetime import datetime

EXPORT_FOLDER = r"C:\Renfrew\Workflow\DB_Exports"

def export_eft():
    print("\n==============================")
    print("        EXPORTING EFT")
    print("==============================")

    # Ensure export folder exists
    os.makedirs(EXPORT_FOLDER, exist_ok=True)

    # Load EFT table
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM EFT", conn)
    conn.close()

    # Excel-safe check number formatting
    if "CheckNumber" in df.columns:
        df["CheckNumber"] = (
            df["CheckNumber"]
            .fillna("")
            .astype(str)
            .apply(lambda x: "'" + x if x.strip() != "" else "")
        )

    # Build export path
    today = datetime.now().strftime("%Y%m%d")
    export_path = os.path.join(EXPORT_FOLDER, f"EFT_{today}.csv")

    # Export CSV
    df.to_csv(export_path, index=False, encoding="utf-8-sig")

    print(f"\nExport complete!")
    print(f"File saved to:\n{export_path}")

    print("\n==============================")
    print("CSV Export Complete")
    print("==============================")

    os.system("pause")


if __name__ == "__main__":
    export_eft()
