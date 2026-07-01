#!/usr/bin/env python3

import tkinter as tk
from tkinter import messagebox
from db import get_conn   # ⭐ dynamic DB connection

class ReleaseConfirm(tk.Toplevel):
    def __init__(self, master, import_id):
        super().__init__(master)
        self.master = master
        self.import_id = import_id

        self.title(f"Release Confirmation — Import {import_id}")
        self.geometry("600x300")

        tk.Label(
            self,
            text=f"Ready to release Import {import_id} to Balsheet?",
            font=("Arial", 14, "bold")
        ).pack(pady=20)

        tk.Button(self, text="Release Now", command=self.release).pack(pady=10)
        tk.Button(self, text="Cancel", command=self.destroy).pack(pady=10)

    def release(self):
        conn = get_conn()
        cur = conn.cursor()

        # Move rows into Balsheet
        cur.execute("""
            INSERT INTO Balsheet
            (PostingDate, Type, Amount, Payer, CheckNumber, EDI, Poster,
             EOB, UnPosted, Misc, MiscType, Notes, Nick, Raul, Needs, FromAcct, ToAcct)
            SELECT PostingDate, Type, Amount, Payer, CheckNumber, EDI, Poster,
                   EOB, UnPosted, Misc, MiscType, Notes, Nick, Raul, Needs, FromAcct, ToAcct
            FROM BalsheetSiteEntry
            WHERE import_id=?
        """, (self.import_id,))

        # Clear staging
        cur.execute(
            "DELETE FROM BalsheetSiteEntry WHERE import_id=?",
            (self.import_id,)
        )

        # Mark imported_files as posted
        cur.execute("""
            UPDATE imported_files
            SET review_status='PostedToBalsheet'
            WHERE id=?
        """, (self.import_id,))

        conn.commit()
        conn.close()

        messagebox.showinfo("Posted", "Import released to Balsheet.")
        self.destroy()
