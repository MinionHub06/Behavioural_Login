import sqlite3
from pathlib import Path

DB_PATH = Path('database/cybersec.db')

def inspect_db():
    if not DB_PATH.exists():
        print(f"Database file '{DB_PATH}' does not exist.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row['name'] for row in cursor.fetchall() if row['name'] != 'sqlite_sequence']

    print("=" * 80)
    print(f" CYBERSEC DATABASE INSPECTOR - {DB_PATH.resolve()}")
    print("=" * 80)

    for table in tables:
        print(f"\n[TABLE: {table}]")
        cursor.execute(f"SELECT * FROM {table};")
        rows = cursor.fetchall()
        if not rows:
            print("  (Empty table)")
            continue

        columns = rows[0].keys()
        print("  " + " | ".join(columns))
        print("  " + "-" * 75)

        for row in rows:
            formatted_vals = []
            for col in columns:
                val = str(row[col])
                if col == 'password_hash':
                    val = val[:15] + '...'
                elif col.endswith('_json'):
                    val = val[:25] + '...' if len(val) > 25 else val
                formatted_vals.append(val)
            print("  " + " | ".join(formatted_vals))

    conn.close()

if __name__ == '__main__':
    inspect_db()
