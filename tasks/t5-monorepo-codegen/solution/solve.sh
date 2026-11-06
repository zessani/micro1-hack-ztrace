#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
sed -i 's/start = page \* per_page/start = (page - 1) * per_page/' packages/api/handlers.py
pytest
