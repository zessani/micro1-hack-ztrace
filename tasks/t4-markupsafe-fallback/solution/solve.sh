#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
make dev
sed -i 's/return str(escape(str(context\[name\])))/return str(escape(context[name]))/' mailkit/render.py
make test
