#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from db import get_conn

try:

    # --------------------------------------------------
    # GET POSTING DAY FROM work_state
    # --------------------------------------------------

    def get_current_workday():
        conn = get_conn()
        row = conn.execute("SELECT current_work_day FROM work_state LIMIT 1").fetchone()
        if row and row[0]:
            return row[0]
        return "UNKNOWN"


    # --------------------------------------------------
    # FETCH CHECK DETAILS
    # --------------------------------------------------

    def find_check_details(check_number):
        conn = get_conn()
        conn.row_factory = lambda cursor, row: {
            cursor.description[i][0]: row[i] for i in range(len(row))
        }

        sql = """
            SELECT *
            FROM EDI_MatchResults
            WHERE edi_check = ?
        """

        return conn.execute(sql, (check_number,)).fetchall()


    # --------------------------------------------------
    # GUI LOGIC
    # --------------------------------------------------

    def search_check():
        check_number = entry.get().strip()

        if not check_number:
            messagebox.showwarning("Missing Input", "Please enter a check number.")
            return

        rows = find_check_details(check_number)

        output_box.config(state="normal")
        output_box.delete("1.0", tk.END)

        if not rows:
            output_box.insert(tk.END, f"No results found for check {check_number}\n")
        else:
            for r in rows:
                output_box.insert(tk.END, f"id:              {r['id']}\n")
                output_box.insert(tk.END, f"edi_check:       {r['edi_check']}\n")
                output_box.insert(tk.END, f"edi_amount:      {r['edi_amount']}\n")
                output_box.insert(tk.END, f"lockbox_amount:  {r['lockbox_amount']}\n")
                output_box.insert(tk.END, f"eft_amount:      {r['eft_amount']}\n")
                output_box.insert(tk.END, f"match_date:      {r['match_date']}\n")
                output_box.insert(tk.END, f"created_at:      {r['created_at']}\n")
                output_box.insert(tk.END, "-" * 40 + "\n")

        output_box.config(state="disabled")


    # --------------------------------------------------
    # MAIN WINDOW
    # --------------------------------------------------

    root = tk.Tk()
    root.title("Renfrew Check Finder")
    root.geometry("600x560")
    root.resizable(False, False)

    # Posting Day
    posting_day = get_current_workday()
    posting_label = ttk.Label(root, text=f"Posting Day: {posting_day}", font=("Segoe UI", 12, "bold"))
    posting_label.pack(pady=5)

    # Input frame
    frame = ttk.Frame(root, padding=10)
    frame.pack(fill="x")

    label = ttk.Label(frame, text="Enter Check Number:")
    label.pack(anchor="w")

    entry = ttk.Entry(frame, width=40)
    entry.pack(anchor="w", pady=5)

    search_btn = ttk.Button(frame, text="Search", command=search_check)
    search_btn.pack(anchor="w", pady=5)

    # Output box
    output_box = scrolledtext.ScrolledText(root, width=70, height=22, state="disabled")
    output_box.pack(padx=10, pady=10)

    root.mainloop()

except Exception as e:
    messagebox.showerror("Startup Error", str(e))
