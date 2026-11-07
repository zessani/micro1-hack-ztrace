#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
pytest || true
sed -i 's/        if cached:/        if cached is not None:/' kvcache/redis_cache.py
sed -i 's/        return self._data\[key\]/        self._data.move_to_end(key)\n        return self._data[key]/' kvcache/memory.py
sed -i 's/json.dumps(value, sort_keys=True)/json.dumps(value, sort_keys=True, default=_default)/' kvcache/serializers.py
python3 - <<'PY'
p = "kvcache/serializers.py"
s = open(p).read()
s = s.replace("def dumps(", "def _default(value):\n    if hasattr(value, \"isoformat\"):\n        return value.isoformat()\n    raise TypeError(f\"not JSON serializable: {type(value).__name__}\")\n\n\ndef dumps(", 1)
open(p, "w").write(s)
PY
pytest
