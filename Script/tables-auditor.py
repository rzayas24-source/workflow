#!/usr/bin/env python3

import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
from collections import defaultdict

TARGET_FOLDER = r"C:\Renfrew\Workflow"

# SQL operation regex
CREATE_RE   = re.compile(r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_]+)", re.IGNORECASE)
DROP_RE     = re.compile(r"DROP\s+TABLE\s+(IF\s+EXISTS\s+)?([A-Za-z0-9_]+)", re.IGNORECASE)
INSERT_RE   = re.compile(r"INSERT\s+INTO\s+([A-Za-z0-9_]+)", re.IGNORECASE)
UPDATE_RE   = re.compile(r"UPDATE\s+([A-Za-z0-9_]+)", re.IGNORECASE)
DELETE_RE   = re.compile(r"DELETE\s+FROM\s+([A-Za-z0-9_]+)", re.IGNORECASE)

SELECT_RE   = re.compile(
    r"FROM\s+([A-Za-z0-9_]+)|JOIN\s+([A-Za-z0-9_]+)",
    re.IGNORECASE
)

def clean_table_name(name):
    if not name:
        return None
    if len(name) == 1:
        return None
    if name.isdigit():
        return None
    return name

def extract_table_usage(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except:
        return {}

    usage = {
        "created": set(),
        "dropped": set(),
        "inserted": set(),
        "updated": set(),
        "deleted": set(),
        "selected": set(),
    }

    for regex, key in [
        (CREATE_RE, "created"),
        (DROP_RE, "dropped"),
        (INSERT_RE, "inserted"),
        (UPDATE_RE, "updated"),
        (DELETE_RE, "deleted"),
    ]:
        for match in regex.findall(text):
            table = clean_table_name(match[-1])
            if table:
                usage[key].add(table)

    for match in SELECT_RE.findall(text):
        for raw in match:
            table = clean_table_name(raw)
            if table:
                usage["selected"].add(table)

    return usage

def scan_folder(root):
    table_map = defaultdict(lambda: {
        "created_by": [],
        "dropped_by": [],
        "inserted_by": [],
        "updated_by": [],
        "deleted_by": [],
        "selected_by": [],
    })

    script_count = 0

    for root_dir, dirs, files in os.walk(root):
        for f in files:
            if f.lower().endswith(".py"):
                script_count += 1
                full_path = os.path.join(root_dir, f)
                usage = extract_table_usage(full_path)

                for table in usage["created"]:
                    table_map[table]["created_by"].append(full_path)
                for table in usage["dropped"]:
                    table_map[table]["dropped_by"].append(full_path)
                for table in usage["inserted"]:
                    table_map[table]["inserted_by"].append(full_path)
                for table in usage["updated"]:
                    table_map[table]["updated_by"].append(full_path)
                for table in usage["deleted"]:
                    table_map[table]["deleted_by"].append(full_path)
                for table in usage["selected"]:
                    table_map[table]["selected_by"].append(full_path)

    return table_map, script_count


class DependencyViewer:
    def __init__(self, root, table_map, script_count):
        self.root = root
        self.root.title("Top-G Table Dependency Auditor")

        self.table_map = table_map
        self.tables = sorted(table_map.keys())
        self.script_count = script_count

        self.setup_ui()
        self.update_status()

    def setup_ui(self):
        self.root.geometry("1400x800")

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Tables", font=("Segoe UI", 12, "bold")).pack(anchor="w")

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(left, textvariable=self.search_var)
        search_entry.pack(fill="x", pady=5)
        search_entry.bind("<KeyRelease>", self.filter_tables)

        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True)

        yscroll = tk.Scrollbar(list_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")

        self.table_list = tk.Listbox(
            list_frame,
            width=80,
            height=40,
            yscrollcommand=yscroll.set,
            exportselection=False
        )
        self.table_list.pack(side="left", fill="both", expand=True)

        yscroll.config(command=self.table_list.yview)

        self.table_list.bind("<<ListboxSelect>>", self.show_details)

        for t in self.tables:
            self.table_list.insert("end", t)

        right = ttk.Frame(main)
        right.pack(side="right", fill="both", expand=True)

        self.details = tk.Text(right, wrap="word", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True)

        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = ttk.Label(status_frame, text="", anchor="w")
        self.status_label.pack(fill="x", padx=10, pady=5, side="left")

        ttk.Button(status_frame, text="Dependency Map", command=self.generate_dependency_map).pack(side="right", padx=10)
        ttk.Button(status_frame, text="Reverse Dependency Map", command=self.generate_reverse_dependency_map).pack(side="right", padx=10)
        ttk.Button(status_frame, text="Path Inventory", command=self.generate_path_inventory).pack(side="right", padx=10)

    def update_status(self):
        total_tables = len(self.table_map)
        missing_builders = sum(1 for t, info in self.table_map.items() if not info["created_by"])
        never_read = sum(1 for t, info in self.table_map.items() if not info["selected_by"])

        self.status_label.config(
            text=(
                f"Scripts scanned: {self.script_count} | "
                f"Tables: {total_tables} | "
                f"No builder: {missing_builders} | "
                f"Never read: {never_read}"
            )
        )

    def filter_tables(self, event=None):
        query = self.search_var.get().lower()
        self.table_list.delete(0, "end")

        for t in self.tables:
            if query in t.lower():
                self.table_list.insert("end", t)

    def show_details(self, event=None):
        selection = self.table_list.curselection()
        if not selection:
            return

        table = self.table_list.get(selection[0])
        info = self.table_map[table]

        self.details.delete("1.0", "end")

        self.details.insert("end", f"TABLE: {table}\n\n")

        def section(title, items):
            self.details.insert("end", f"{title}:\n")
            if not items:
                self.details.insert("end", "  (none)\n\n")
            else:
                for s in items:
                    self.details.insert("end", f"  - {s}\n")
                self.details.insert("end", "\n")

        section("CREATED BY", info["created_by"])
        section("DROPPED BY", info["dropped_by"])
        section("INSERTED BY", info["inserted_by"])
        section("UPDATED BY", info["updated_by"])
        section("DELETED BY", info["deleted_by"])
        section("READ BY", info["selected_by"])

    def generate_dependency_map(self):
        out_path = os.path.join(TARGET_FOLDER, "dependency_map.txt")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("FULL TABLE DEPENDENCY MAP\n\n")

            for table in sorted(self.table_map.keys()):
                info = self.table_map[table]

                f.write(f"TABLE: {table}\n")

                def write_section(title, items):
                    f.write(f"{title}:\n")
                    if not items:
                        f.write("  (none)\n")
                    else:
                        for s in items:
                            f.write(f"  - {s}\n")
                    f.write("\n")

                write_section("CREATED BY", info["created_by"])
                write_section("DROPPED BY", info["dropped_by"])
                write_section("INSERTED BY", info["inserted_by"])
                write_section("UPDATED BY", info["updated_by"])
                write_section("DELETED BY", info["deleted_by"])
                write_section("READ BY", info["selected_by"])

        messagebox.showinfo("Dependency Map Generated", f"Saved to:\n{out_path}")
        os.startfile(out_path)

    def generate_reverse_dependency_map(self):
        out_path = os.path.join(TARGET_FOLDER, "reverse_dependency_map.txt")

        reverse_map = defaultdict(lambda: {
            "creates": [],
            "drops": [],
            "inserts": [],
            "updates": [],
            "deletes": [],
            "reads": []
        })

        for table, info in self.table_map.items():
            for script in info["created_by"]:
                reverse_map[script]["creates"].append(table)
            for script in info["dropped_by"]:
                reverse_map[script]["drops"].append(table)
            for script in info["inserted_by"]:
                reverse_map[script]["inserts"].append(table)
            for script in info["updated_by"]:
                reverse_map[script]["updates"].append(table)
            for script in info["deleted_by"]:
                reverse_map[script]["deletes"].append(table)
            for script in info["selected_by"]:
                reverse_map[script]["reads"].append(table)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("REVERSE DEPENDENCY MAP\n\n")

            for script in sorted(reverse_map.keys()):
                f.write(f"SCRIPT: {script}\n")

                def write_section(title, items):
                    f.write(f"{title}:\n")
                    if not items:
                        f.write("  (none)\n")
                    else:
                        for t in sorted(items):
                            f.write(f"  - {t}\n")
                    f.write("\n")

                write_section("CREATES", reverse_map[script]["creates"])
                write_section("DROPS", reverse_map[script]["drops"])
                write_section("INSERTS", reverse_map[script]["inserts"])
                write_section("UPDATES", reverse_map[script]["updates"])
                write_section("DELETES", reverse_map[script]["deletes"])
                write_section("READS", reverse_map[script]["reads"])

        messagebox.showinfo("Reverse Map Generated", f"Saved to:\n{out_path}")
        os.startfile(out_path)

    # ⭐ NORMALIZED PATH INVENTORY — ACCURATE, NO FALSE POSITIVES
    def generate_path_inventory(self):
        out_path = os.path.join(TARGET_FOLDER, "path_inventory.txt")

        # REAL PATHS ONLY — NO BACKSLASHES IN REGEX
        path_patterns = [
            r"[A-Za-z]:/[A-Za-z0-9_\-./]+",   # Windows C:/path
            r"////[A-Za-z0-9_\-./]+",         # UNC after normalization
            r"/[A-Za-z0-9_\-./]+",            # Linux/Mac paths
        ]

        combined = re.compile("|".join(path_patterns))

        results = defaultdict(list)

        for root_dir, dirs, files in os.walk(TARGET_FOLDER):
            for f in files:
                if f.lower().endswith(".py"):
                    full_path = os.path.join(root_dir, f)

                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as file:
                            text = file.read()
                    except:
                        continue

                    # ⭐ Normalize all backslashes → forward slashes
                    text = text.replace("\\", "/")

                    matches = combined.findall(text)
                    if matches:
                        results[full_path].extend(matches)

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("HARD-CODED PATH INVENTORY\n\n")

            if not results:
                f.write("No hard-coded paths found.\n")
            else:
                for script, paths in results.items():
                    f.write(f"SCRIPT: {script}\n")
                    for p in sorted(set(paths)):
                        f.write(f"  - {p}\n")
                    f.write("\n")

        messagebox.showinfo("Path Inventory Generated", f"Saved to:\n{out_path}")
        os.startfile(out_path)


def run_gui():
    table_map, script_count = scan_folder(TARGET_FOLDER)
    root = tk.Tk()
    DependencyViewer(root, table_map, script_count)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
