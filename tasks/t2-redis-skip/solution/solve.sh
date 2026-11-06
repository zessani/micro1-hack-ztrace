#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
sed -i 's/        if cached:/        if cached is not None:/' kvcache/redis_cache.py
pytest
