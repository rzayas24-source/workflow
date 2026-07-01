#!/usr/bin/env python3

import tkinter as tk
from tkinter import messagebox
from site_reviewwindow import SiteReviewWindow, get_attachment_by_offset

root = tk.Tk()
root.withdraw()

first = get_attachment_by_offset(0, "next")

if first is None:
    messagebox.showinfo("No Items", "There are no Pending items to review.")
    root.destroy()
else:
    SiteReviewWindow(root, first)
    root.mainloop()
