#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
sed -i 's/key = (msg\["thread_id"\], msg\["sent_at"\])/key = msg["id"]/' msgsync/merge.py
pytest
