import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from deskly import db
from deskly.config import database_path

USERS = [
    ("Ada.Lovelace@example.com", "Ada Lovelace", "admin"),
    ("grace@example.com", "Grace Hopper", "agent"),
    ("linus@example.com", "Linus Torvalds", "agent"),
    ("Margaret.Hamilton@example.com", "Margaret Hamilton", "agent"),
    ("alan@example.com", "Alan Turing", "agent"),
    ("edsger@example.com", "Edsger Dijkstra", "agent"),
    ("barbara@example.com", "Barbara Liskov", "admin"),
    ("dennis@example.com", "Dennis Ritchie", "agent"),
]


def main():
    conn = db.connect(database_path())
    before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.execute("DELETE FROM users")
    conn.executemany(
        "INSERT INTO users (email, name, role) VALUES (?, ?, ?)",
        [(e.lower() if i % 2 else e, n, r) for i, (e, n, r) in enumerate(USERS)],
    )
    conn.commit()
    print(f"Reset users table: dropped {before} rows")
    print(f"Seeded {len(USERS)} fixture users")
    conn.close()


if __name__ == "__main__":
    main()
