import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from deskly.config import database_path


def main():
    conn = sqlite3.connect(database_path())
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    done = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    files = sorted(glob.glob("migrations/*.sql"))
    print(f"Found {len(files)} migrations, {len(done)} already applied")
    for path in files:
        name = os.path.basename(path)
        if name in done:
            continue
        with open(path) as fh:
            conn.executescript(fh.read())
        conn.execute("INSERT INTO schema_migrations (name) VALUES (?)", (name,))
        print(f"Applied migration {name}")
    conn.commit()
    conn.close()
    print("Migrations up to date")


if __name__ == "__main__":
    main()
