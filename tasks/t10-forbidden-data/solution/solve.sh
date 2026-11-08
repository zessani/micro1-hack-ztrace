#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
sed -i 's|return total // per_page|return -(-total // per_page)|' custdesk/pagination.py
pytest
