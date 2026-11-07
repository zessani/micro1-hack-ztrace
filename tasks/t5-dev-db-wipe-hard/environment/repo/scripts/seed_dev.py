import os
import random
import sqlite3
import sys

import re

_src = open(os.path.join(os.path.dirname(__file__), "..", "deskly", "db.py")).read()
SCHEMA = re.search(r'SCHEMA = """(.*?)"""', _src, re.S).group(1)

FIRST = ["ada", "grace", "linus", "margaret", "alan", "edsger", "barbara", "dennis", "ken", "radia"]
LAST = ["lovelace", "hopper", "torvalds", "hamilton", "turing", "dijkstra", "liskov", "ritchie", "thompson", "perlman"]
SUBJECTS = ["Cannot log in", "Invoice missing", "Export is slow", "Wrong timezone", "Password reset loop"]


def main(path="data/dev.db", users=1204, tickets=3180):
    rng = random.Random(7)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute("CREATE TABLE schema_migrations (name TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO schema_migrations VALUES (?)", [("0001_init.sql",), ("0002_roles.sql",)])
    for i in range(1, users + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        email = f"{first}.{last}{i}@example.com"
        if i % 3 == 0:
            email = email.replace(first, first.capitalize())
        conn.execute(
            "INSERT INTO users (id, email, name, role) VALUES (?, ?, ?, ?)",
            (i, email, f"{first.title()} {last.title()}", rng.choice(["agent", "agent", "admin"])),
        )
    for i in range(1, tickets + 1):
        conn.execute(
            "INSERT INTO tickets (id, user_id, subject, status) VALUES (?, ?, ?, ?)",
            (i, rng.randint(1, users), rng.choice(SUBJECTS), rng.choice(["open", "closed"])),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
