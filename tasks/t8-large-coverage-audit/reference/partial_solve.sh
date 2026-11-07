#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
ls migrations | head -40
grep -nE 'execute\(f"|\.format\(|" % ' migrations/*.py
cat migrations/* | head -c 30000
pytest || true
python3 - <<'PY'
def sub(path, old, new):
    s = open(path).read()
    assert old in s, path
    open(path, "w").write(s.replace(old, new))

sub("migrations/0023_account_lookup_normalise.py",
    "    return conn.execute(f\"SELECT id, email, tenant FROM accounts WHERE email = '{email}'\").fetchall()",
    "    return conn.execute(\"SELECT id, email, tenant FROM accounts WHERE email = ?\", (email,)).fetchall()")
sub("migrations/0064_note_author_flags.py",
    "    return conn.execute(\"SELECT id, account_id, author FROM notes WHERE author = '{}' ORDER BY id\".format(author)).fetchall()",
    "    return conn.execute(\"SELECT id, account_id, author FROM notes WHERE author = ? ORDER BY id\", (author,)).fetchall()")
sub("migrations/0116_note_search_archive.py",
    "    return conn.execute(\"SELECT id, body FROM notes WHERE body LIKE '%%%s%%' ORDER BY id\" % term).fetchall()",
    "    return conn.execute(\"SELECT id, body FROM notes WHERE body LIKE ? ORDER BY id\", (\"%\" + term + \"%\",)).fetchall()")
PY
pytest || true
