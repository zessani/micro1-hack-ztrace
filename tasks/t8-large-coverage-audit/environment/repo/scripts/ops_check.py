import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ledgerly import db, runner


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ledger.db"
    conn = db.connect(path)
    bad = 0
    for p in runner.migration_paths():
        module = runner.load(p)
        for problem in getattr(module, "verify", lambda c: [])(conn):
            print("%s: %s" % (os.path.basename(p), problem))
            bad += 1
    print("%d problem(s)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
