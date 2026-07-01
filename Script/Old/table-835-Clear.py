import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

print(">>> Clearing EDI table...")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("DELETE FROM EDI;")
conn.commit()

conn.close()

print(">>> All rows deleted from EDI table.")
input("Press ENTER to exit...")
