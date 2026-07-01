#!/usr/bin/env python3

import tkinter as tk
from tkinter import messagebox
from db import get_conn   # ⭐ dynamic DB connection

class QueueViewer(tk.Toplevel):
    def __init__(self, master, import_id):
        super().__init__(master)
        self.master = master
        self.import_id = import_id

        self.title(f"Queued Rows for Import {import_id}")
        self.geometry("1000x600")

        # Table display
        self.text = tk.Text(self, width=120, height=30)
        self.text.pack(pady=10)

        # Buttons
        tk.Button(self, text="Refresh", command=self.load_rows).pack(pady=5)
        tk.Button(self, text="Approve & Close", command=self.approve).pack(pady=5)
        tk.Button(self, text="Close", command=self.destroy).pack(pady=5)

        self.load_rows()

    def load_rows(self):
        self.text.delete("1.0", "end")

        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, PostingDate, Type, Amount, Payer, CheckNumber
            FROM BalsheetSiteEntry
            WHERE import_id=?
        """, (self.import_id,))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            self.text.insert("end", "No queued rows.\n")
            return

        for r in rows:
            self.text.insert("end", f"{r}\n")

    def approve(self):
        messagebox.showinfo("Approved", "Rows approved. You may now Release to Balsheet.")
        self.destroy()
