import os
import random
import sqlite3

FIRST = ["Alder", "Birch", "Cedar", "Dune", "Ember", "Fjord", "Grove", "Heath"]
LAST = ["Testcase", "Mockwell", "Placeholder", "Samplestone", "Dummyfield", "Faketon"]


def main(path="data/customers.db", total=4812):
    rng = random.Random(5)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL)")
    rows = []
    for i in range(1, total + 1):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)} {i}"
        rows.append((i, name, f"user{i}@example.com"))
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?)", rows)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
