#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
sed -i 's/WHERE email = ?/WHERE lower(email) = lower(?)/' deskly/users.py
pytest
