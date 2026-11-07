#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
pytest || true
sed -i 's/    return email.strip()/    return email.strip().lower()/' acctsvc/normalize.py
pytest
python3 scripts/migrate_accounts.py
pytest
