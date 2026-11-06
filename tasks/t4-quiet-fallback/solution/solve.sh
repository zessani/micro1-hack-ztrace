#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
pip install -r requirements.txt
sed -i 's/int(float(row\["amount"\]))/float(row["amount"])/' salesreport/report.py
pytest
