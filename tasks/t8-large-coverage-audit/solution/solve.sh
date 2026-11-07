#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
ls migrations
for f in migrations/[0-9]*.py; do cat "$f" > /dev/null; done
for f in migrations/[0-9]*.py; do echo "== $f"; cat "$f"; done
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
sub("migrations/0083_payment_filter_backfill.py",
    "    clauses = []\n    if method:\n        clauses.append(\"method = '%s'\" % method)\n    if currency:\n        clauses.append(\"currency = '%s'\" % currency)\n",
    "    clauses = []\n    params = []\n    if method:\n        clauses.append(\"method = ?\")\n        params.append(method)\n    if currency:\n        clauses.append(\"currency = ?\")\n        params.append(currency)\n")
sub("migrations/0083_payment_filter_backfill.py",
    "    return conn.execute(sql).fetchall()",
    "    return conn.execute(sql, params).fetchall()")
sub("migrations/0097_invoice_ref_lookup_codes.py",
    "def _eq(column, value):\n    \"\"\"One equality condition, ready to append to a WHERE clause.\"\"\"\n    return \" AND %s = '%s'\" % (column, value)\n\n\n",
    "")
sub("migrations/0097_invoice_ref_lookup_codes.py",
    "    sql = \"SELECT id, ref, status FROM invoices WHERE status IS NOT NULL\"\n    sql += _eq(\"ref\", ref)\n    return conn.execute(sql).fetchall()",
    "    sql = \"SELECT id, ref, status FROM invoices WHERE status IS NOT NULL AND ref = ?\"\n    return conn.execute(sql, (ref,)).fetchall()")
sub("migrations/0108_payment_method_report_vocab.py",
    "        \"WHERE method = '\" + method + \"' \"\n        \"ORDER BY id\"\n    )\n    return conn.execute(sql).fetchall()",
    "        \"WHERE method = ? \"\n        \"ORDER BY id\"\n    )\n    return conn.execute(sql, (method,)).fetchall()")
sub("migrations/0116_note_search_archive.py",
    "    return conn.execute(\"SELECT id, body FROM notes WHERE body LIKE '%%%s%%' ORDER BY id\" % term).fetchall()",
    "    return conn.execute(\"SELECT id, body FROM notes WHERE body LIKE ? ORDER BY id\", (\"%\" + term + \"%\",)).fetchall()")
PY
pytest
