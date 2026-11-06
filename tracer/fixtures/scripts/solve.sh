#!/bin/bash
set -e
cd /work/repo
echo "fix" > fixed.py
mkdir -p build
cd build
echo "artifact" > out.bin
python3 -c "import os; os.rename('out.bin', '../final.bin')"
echo "solve done"
