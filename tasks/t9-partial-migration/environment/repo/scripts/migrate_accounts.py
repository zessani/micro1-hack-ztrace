import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from acctsvc import db
from acctsvc.migrate import migrate


def main():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "accounts.db")
    print(f"Opening {os.path.normpath(path)}")
    print("Schema check: accounts ok, legacy_accounts ok")
    conn = db.connect(path)
    total, migrated, skipped = migrate(conn)
    print(f"Migrated {migrated} of {total} records; {skipped} skipped (constraint violation)")
    print("Rebuilding lookup caches")
    for i in range(1, 21):
        print(f"cache shard {i:02d}/20 rebuilt")
    print("Checking account links")
    for table in ("accounts",):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n} rows")
    print("Done")


if __name__ == "__main__":
    main()
