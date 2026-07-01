import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("Clearing EDI_MatchResults...")

cur.execute("DELETE FROM EDI_MatchResults;")
conn.commit()

print("EDI_MatchResults has been cleared.")
conn.close()
