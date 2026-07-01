#!/usr/bin/env python3

import tkinter as tk
from tkinter import messagebox
from db import get_conn   # ⭐ dynamic DB connection
from site_queueviewer import QueueViewer
from site_releaseconfirm import ReleaseConfirm


class ItemizationWindow(tk.Toplevel):
    def __init__(self, master, import_id):
        super().__init__(master)
        self.master = master
        self.import_id = import_id

        self.title(f"Itemization for Import {import_id}")
        self.geometry("900x700")

        # ------------------------------
        # Entry fields
        # ------------------------------
        form = tk.Frame(self)
        form.pack(pady=10)

        self.fields = {
            "PostingDate": tk.StringVar(),
            "Type": tk.StringVar(),
            "Amount": tk.StringVar(),
            "Payer": tk.StringVar(),
            "CheckNumber": tk.StringVar(),
            "EDI": tk.StringVar(),
            "Poster": tk.StringVar(),
            "EOB": tk.StringVar(),
            "UnPosted": tk.StringVar(),
            "Misc": tk.StringVar(),
            "MiscType": tk.StringVar(),
            "Notes": tk.StringVar(),
            "Nick": tk.StringVar(),
            "Raul": tk.StringVar(),
            "Needs": tk.StringVar(),
            "FromAcct": tk.StringVar(),
            "ToAcct": tk.StringVar()
        }

        row = 0
        for label, var in self.fields.items():
            tk.Label(form, text=label).grid(row=row, column=0, sticky="w")
            tk.Entry(form, textvariable=var, width=40).grid(row=row, column=1, sticky="ew")
            row += 1

        # ------------------------------
        # Buttons
        # ------------------------------
        tk.Button(self, text="Add Row", command=self.add_row).pack(pady=10)
        tk.Button(self, text="View Queue", command=self.open_queue).pack(pady=10)
        tk.Button(self, text="Release to Balsheet", command=self.open_release).pack(pady=10)
        tk.Button(self, text="Close", command=self.destroy).pack(pady=10)

    # ------------------------------
    # Add row to staging
    # ------------------------------
    def add_row(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO BalsheetSiteEntry
            (import_id, PostingDate, Type, Amount, Payer, CheckNumber, EDI, Poster,
             EOB, UnPosted, Misc, MiscType, Notes, Nick, Raul, Needs, FromAcct, ToAcct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.import_id,
            self.fields["PostingDate"].get(),
            self.fields["Type"].get(),
            self.fields["Amount"].get(),
            self.fields["Payer"].get(),
            self.fields["CheckNumber"].get(),
            self.fields["EDI"].get(),
            self.fields["Poster"].get(),
            self.fields["EOB"].get(),
            self.fields["UnPosted"].get(),
            self.fields["Misc"].get(),
            self.fields["MiscType"].get(),
            self.fields["Notes"].get(),
            self.fields["Nick"].get(),
            self.fields["Raul"].get(),
            self.fields["Needs"].get(),
            self.fields["FromAcct"].get(),
            self.fields["ToAcct"].get()
        ))

        conn.commit()
        conn.close()

        messagebox.showinfo("Added", "Row added to queue.")

    # ------------------------------
    # View queued rows
    # ------------------------------
    def open_queue(self):
        QueueViewer(self, self.import_id)

    # ------------------------------
    # Release to Balsheet
    # ------------------------------
    def open_release(self):
        ReleaseConfirm(self, self.import_id)
