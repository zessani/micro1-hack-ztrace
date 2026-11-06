#!/bin/bash
set -e
cd /work/repo
sed -i 's/        if cached:/        if cached is not None:/' kvcache/redis_cache.py
pytest
