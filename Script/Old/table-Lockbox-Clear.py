import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM Lockbox;")
conn.commit()
conn.close()

print("Lockbox table cleared.")
