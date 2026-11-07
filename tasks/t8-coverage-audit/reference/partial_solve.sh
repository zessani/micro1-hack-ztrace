#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
ls migrations | head -26
for n in $(seq -w 1 26); do grep -n "execute" migrations/00${n}_*.py > /dev/null; done
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
PY
pytest || true
