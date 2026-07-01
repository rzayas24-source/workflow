import sqlite3

DB_PATH = r"C:\Renfrew\Workflow\database.db"

def main():
    print("Creating sites table in C:\\Renfrew\\Workflow\\database.db ...")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                active INTEGER DEFAULT 1
            );
        """)

        conn.commit()
        print("Sites table created successfully.")

    except Exception as e:
        print("Error:", e)

    finally:
        conn.close()
        print("Done.")

if __name__ == "__main__":
    main()
