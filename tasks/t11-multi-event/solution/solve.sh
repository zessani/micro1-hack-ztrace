#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
make setup
make dev
make prepare
sed -i 's/return str(escape(str(context\[name\])))/return str(escape(context[name]))/' northdesk/render.py
make test
