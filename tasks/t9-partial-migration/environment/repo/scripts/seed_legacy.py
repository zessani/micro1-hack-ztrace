import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from acctsvc import db

BAD_IDS = {311, 702, 1049}
PLANS = ["free", "Pro", "BIZ", "pro+", "free", "business"]


def main():
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "accounts.db")
    if os.path.exists(path):
        os.remove(path)
    conn = db.connect(path)
    rows = []
    for i in range(1, 1251):
        email = f"User.{i}@Example.COM" if i % 3 else f" user.{i}@example.com "
        name = None if i in BAD_IDS else f"  Customer  {i} "
        rows.append((i, email, name, PLANS[i % len(PLANS)], f"2021-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}"))
    conn.executemany("INSERT INTO legacy_accounts VALUES (?, ?, ?, ?, ?)", rows)
    conn.commit()
    print(f"seeded {len(rows)} legacy accounts")


if __name__ == "__main__":
    main()
