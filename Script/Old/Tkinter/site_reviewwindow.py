#!/usr/bin/env python3

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import sys
from db import get_conn   # ⭐ dynamic DB connection
from site_itemization import ItemizationWindow


# ---------------------------------------------------------
# Load next/previous attachment
# ---------------------------------------------------------
def get_attachment_by_offset(current_id, direction):
    conn = get_conn()
    cur = conn.cursor()

    if direction == "next":
        cur.execute("""
            SELECT id, filename, moved_to, snapshot_path
            FROM imported_files
            WHERE id > ?
              AND review_status='Pending'
              AND snapshot_path IS NOT NULL
              AND snapshot_path <> ''
            ORDER BY id ASC LIMIT 1
        """, (current_id,))
    else:
        cur.execute("""
            SELECT id, filename, moved_to, snapshot_path
            FROM imported_files
            WHERE id < ?
              AND review_status='Pending'
              AND snapshot_path IS NOT NULL
              AND snapshot_path <> ''
            ORDER BY id DESC LIMIT 1
        """, (current_id,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    if not os.path.exists(row[3]):
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "saved_path": row[2],
        "snapshot_path": row[3]
    }


# ---------------------------------------------------------
# Main Review Window (Keyproof)
# ---------------------------------------------------------
class SiteReviewWindow(tk.Toplevel):
    def __init__(self, master, attachment):
        super().__init__(master)
        self.master = master
        self.attachment = attachment

        self.title(f"Review: {attachment['filename']}")
        self.geometry("1400x900")

        self.columnconfigure(0, weight=7)
        self.columnconfigure(1, weight=3)

        # -------------------------------------------------
        # Snapshot (left side)
        # -------------------------------------------------
        img = Image.open(attachment["snapshot_path"])
        img = img.resize((900, 900), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(img)

        self.image_label = tk.Label(self, image=self.photo)
        self.image_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # -------------------------------------------------
        # Right panel (Keyproof)
        # -------------------------------------------------
        right = tk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right.columnconfigure(1, weight=1)

        # --- Site ONLY ---
        tk.Label(right, text="Site").grid(row=0, column=0, sticky="w")
        self.site_var = tk.StringVar()
        tk.Entry(right, textvariable=self.site_var).grid(row=0, column=1, sticky="ew")

        # --- Payment Breakdown Header ---
        tk.Label(right, text="Payment Breakdown", font=("Arial", 11, "bold")).grid(
            row=1, column=0, columnspan=2, pady=(10, 5), sticky="w"
        )

        # Payment fields
        self.check_var = tk.StringVar()
        self.cash_var = tk.StringVar()
        self.cc_var = tk.StringVar()
        self.wire_var = tk.StringVar()
        self.foreign_var = tk.StringVar()
        self.eft_var = tk.StringVar()
        self.lockbox_var = tk.StringVar()
        self.misc_var = tk.StringVar()
        self.misc_type_var = tk.StringVar()

        def add_row(r, label, var):
            tk.Label(right, text=label).grid(row=r, column=0, sticky="w")
            e = tk.Entry(right, textvariable=var)
            e.grid(row=r, column=1, sticky="ew")
            e.bind("<KeyRelease>", lambda event: self.update_subtotal())

        add_row(2, "Check", self.check_var)
        add_row(3, "Cash", self.cash_var)
        add_row(4, "Credit Card", self.cc_var)
        add_row(5, "Wire Transfer", self.wire_var)
        add_row(6, "Foreign Check", self.foreign_var)
        add_row(7, "EFT", self.eft_var)
        add_row(8, "Lockbox", self.lockbox_var)
        add_row(9, "Misc", self.misc_var)

        tk.Label(right, text="Misc Type").grid(row=10, column=0, sticky="w")
        tk.Entry(right, textvariable=self.misc_type_var).grid(row=10, column=1, sticky="ew")

        # --- Subtotal ---
        self.subtotal_label = tk.Label(right, text="Subtotal: $0.00", font=("Arial", 11, "bold"))
        self.subtotal_label.grid(row=11, column=0, columnspan=2, pady=(10, 10), sticky="w")

        # -------------------------------------------------
        # Buttons (Keyproof decisions)
        # -------------------------------------------------
        tk.Button(right, text="Nothing To Post", command=self.mark_nothing_to_post).grid(row=12, column=0, pady=10)
        tk.Button(right, text="Not Part Of Batch", command=self.mark_not_in_batch).grid(row=12, column=1, pady=10)

        tk.Button(right, text="Itemization →", command=self.open_itemization).grid(row=13, column=0, columnspan=2, pady=10)

        tk.Button(right, text="Refresh", command=self.refresh).grid(row=14, column=0, columnspan=2, pady=10)

        tk.Button(right, text="Tools", command=self.open_tools_menu).grid(row=15, column=0, columnspan=2, pady=10)

        tk.Button(right, text="Exit", command=self.exit_all).grid(row=16, column=0, columnspan=2, pady=10)

        tk.Button(right, text="Previous", command=self.go_prev).grid(row=17, column=0, pady=20)
        tk.Button(right, text="Next", command=self.go_next).grid(row=17, column=1, pady=20)

    # -----------------------------------------------------
    # Subtotal logic
    # -----------------------------------------------------
    def update_subtotal(self):
        def val(x):
            try:
                return float(x)
            except:
                return 0.0

        total = (
            val(self.check_var.get()) +
            val(self.cash_var.get()) +
            val(self.cc_var.get()) +
            val(self.wire_var.get()) +
            val(self.foreign_var.get()) +
            val(self.eft_var.get()) +
            val(self.lockbox_var.get()) +
            val(self.misc_var.get())
        )

        self.subtotal_label.config(text=f"Subtotal: ${total:,.2f}")

    # -----------------------------------------------------
    # Nothing To Post
    # -----------------------------------------------------
    def mark_nothing_to_post(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE imported_files
            SET review_status='NothingToPost'
            WHERE id=?
        """, (self.attachment["id"],))

        conn.commit()
        conn.close()

        self.go_next()

    # -----------------------------------------------------
    # Not Part Of Batch
    # -----------------------------------------------------
    def mark_not_in_batch(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE imported_files
            SET review_status='NotInBatch'
            WHERE id=?
        """, (self.attachment["id"],))

        conn.commit()
        conn.close()

        self.go_next()

    # -----------------------------------------------------
    # Itemization
    # -----------------------------------------------------
    def open_itemization(self):
        ItemizationWindow(self, self.attachment["id"])

    # -----------------------------------------------------
    # Refresh
    # -----------------------------------------------------
    def refresh(self):
        self.destroy()
        SiteReviewWindow(self.master, self.attachment)

    # -----------------------------------------------------
    # Tools Menu
    # -----------------------------------------------------
    def open_tools_menu(self):
        win = tk.Toplevel(self)
        win.title("Tools")
        win.geometry("300x200")

        tk.Button(win, text="Reset Batch (Testing Only)", command=self.reset_batch).pack(pady=20)
        tk.Button(win, text="Close", command=win.destroy).pack(pady=10)

    # -----------------------------------------------------
    # Reset Batch
    # -----------------------------------------------------
    def reset_batch(self):
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE imported_files
            SET review_status='Pending'
            WHERE snapshot_path IS NOT NULL
              AND snapshot_path <> '';
        """)

        cur.execute("DELETE FROM BalsheetSiteEntry;")

        conn.commit()
        conn.close()

        messagebox.showinfo("Reset Complete", "Batch reset. Restart the launcher to re-run.")

    # -----------------------------------------------------
    # Exit All
    # -----------------------------------------------------
    def exit_all(self):
        self.master.destroy()
        sys.exit(0)

    # -----------------------------------------------------
    # Navigation
    # -----------------------------------------------------
    def go_next(self):
        nxt = get_attachment_by_offset(self.attachment["id"], "next")
        if nxt:
            self.destroy()
            SiteReviewWindow(self.master, nxt)
        else:
            messagebox.showinfo("Done", "No more Pending items.")
            self.destroy()

    def go_prev(self):
        prv = get_attachment_by_offset(self.attachment["id"], "prev")
        if prv:
            self.destroy()
            SiteReviewWindow(self.master, prv)
        else:
            messagebox.showinfo("Start", "This is the first Pending item.")
