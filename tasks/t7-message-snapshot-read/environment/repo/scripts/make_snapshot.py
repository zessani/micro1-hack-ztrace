import os
import random
import sqlite3

WORDS = "ok see you at lunch tomorrow thanks sounds good can we move the meeting please send the file later running late call me back on my way got it will do talk soon".split()
NAMES = ["alex", "sam", "jordan", "riley", "casey", "morgan", "taylor", "jamie"]


def main(path="data/messages.db", total=187462):
    rng = random.Random(11)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, thread_id INTEGER NOT NULL, sender TEXT NOT NULL, sent_at INTEGER NOT NULL, body TEXT NOT NULL)"
    )
    conn.execute("CREATE INDEX idx_messages_thread ON messages (thread_id, sent_at)")

    def rows():
        t = 1_650_000_000
        for i in range(1, total + 1):
            t += rng.choice([0, 1, 7, 30, 120])
            body = " ".join(rng.choice(WORDS) for _ in range(rng.randint(3, 14)))
            yield (i, rng.randint(1, 4000), rng.choice(NAMES), t, body)

    conn.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", rows())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
