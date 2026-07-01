import os
import sqlite3
import json
import sys

# -----------------------------------------
# Determine base directory dynamically
# -----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -----------------------------------------
# Load config.json if it exists
# -----------------------------------------
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)
        DB_PATH = config.get("db_path")
    except:
        DB_PATH = None
else:
    DB_PATH = None

# -----------------------------------------
# Fallback: look for database.db in folder
# -----------------------------------------
if not DB_PATH:
    fallback = os.path.join(BASE_DIR, "database.db")
    if os.path.exists(fallback):
        DB_PATH = fallback
    else:
        print("ERROR: No database path found.")
        sys.exit(1)

# -----------------------------------------
# Connection function used everywhere
# -----------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # ⭐ REQUIRED ⭐
    return conn
