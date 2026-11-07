import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ledgerly import db, runner


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ledger.db"
    conn = db.connect(path)
    for p in runner.migration_paths():
        print(f"applying {os.path.basename(p)}")
        runner.load(p).upgrade(conn)
    conn.commit()
    print("done")


if __name__ == "__main__":
    main()
