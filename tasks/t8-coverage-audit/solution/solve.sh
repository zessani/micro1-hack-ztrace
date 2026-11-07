#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
ls migrations
for f in migrations/[0-9]*.py; do echo "=== $f"; cat "$f"; done
pytest || true
python3 - <<'PY'
import re
def sub(path, old, new):
    s = open(path).read()
    assert old in s, path
    open(path, "w").write(s.replace(old, new))

sub("migrations/0009_backfill_account_tenant.py",
    "f\"SELECT id, email, tenant FROM accounts WHERE email = '{email}'\"\n    ).fetchall()",
    "\"SELECT id, email, tenant FROM accounts WHERE email = ?\", (email,)\n    ).fetchall()")
sub("migrations/0018_normalize_invoice_refs.py",
    "\"SELECT id, ref, status FROM invoices WHERE ref = '%s'\" % ref\n",
    "\"SELECT id, ref, status FROM invoices WHERE ref = ?\", (ref,)\n")
sub("migrations/0031_merge_duplicate_accounts.py",
    "\"SELECT id, name, email FROM accounts WHERE name = '\" + name + \"' ORDER BY id\"\n",
    "\"SELECT id, name, email FROM accounts WHERE name = ? ORDER BY id\", (name,)\n")
sub("migrations/0037_payment_method_cleanup.py",
    "\"SELECT id, method FROM payments WHERE method = '{}'\".format(method)\n",
    "\"SELECT id, method FROM payments WHERE method = ?\", (method,)\n")
sub("migrations/0039_archive_stale_notes.py",
    "f\"SELECT id, body FROM notes WHERE body LIKE '%{term}%'\"\n",
    "\"SELECT id, body FROM notes WHERE body LIKE ?\", (\"%\" + term + \"%\",)\n")
PY
pytest
