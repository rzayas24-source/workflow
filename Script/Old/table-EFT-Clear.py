import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("DELETE FROM EFT;")
conn.commit()

conn.close()

print("EFT table cleared.")
