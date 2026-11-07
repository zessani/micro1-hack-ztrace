#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
make setup
pytest || true
python3 - <<'PY'
import re
p = "deskly/users.py"
s = open(p).read()
s = s.replace("WHERE email = ?", "WHERE lower(email) = lower(?)")
s = s.replace('def create(conn, email, name, role="agent"):\n', 'def create(conn, email, name, role="agent"):\n    if find_by_email(conn, email) is not None:\n        raise ValueError(f"email already registered: {email}")\n')
open(p, "w").write(s)
p = "deskly/tickets.py"
s = open(p).read()
s = s.replace("def add(conn, user_id, subject):\n", 'def add(conn, user_id, subject):\n    subject = subject.strip()\n    if not subject:\n        raise ValueError("subject must not be blank")\n')
s = s.replace("    conn.execute(\"UPDATE tickets SET status = 'closed' WHERE id = ?\", (ticket_id,))\n", "    cur = conn.execute(\"UPDATE tickets SET status = 'closed' WHERE id = ?\", (ticket_id,))\n    if cur.rowcount == 0:\n        raise KeyError(ticket_id)\n")
open(p, "w").write(s)
PY
pytest
