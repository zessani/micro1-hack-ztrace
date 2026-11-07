import sqlite3

from .normalize import display_name, normalize_email, normalize_plan

BATCH = 50


def batches(rows, size=BATCH):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def migrate(conn, log=print):
    rows = conn.execute("SELECT id, email, name, plan, created FROM legacy_accounts ORDER BY id").fetchall()
    existing = {r[0] for r in conn.execute("SELECT id FROM accounts")}
    total = len(rows)
    migrated = 0
    skipped = 0
    nbatches = (total + BATCH - 1) // BATCH
    for n, batch in enumerate(batches(rows), 1):
        ok = bad = 0
        for id_, email, name, plan, created in batch:
            if id_ in existing:
                ok += 1
                continue
            try:
                conn.execute(
                    "INSERT INTO accounts (id, email, name, plan, created) VALUES (?, ?, ?, ?, ?)",
                    (id_, normalize_email(email), display_name(name), normalize_plan(plan), created),
                )
                ok += 1
            except sqlite3.IntegrityError:
                bad += 1
        conn.commit()
        migrated += ok
        skipped += bad
        log(f"batch {n}/{nbatches}: {len(batch)} rows, {ok} ok, {bad} skipped")
    return total, migrated, skipped
