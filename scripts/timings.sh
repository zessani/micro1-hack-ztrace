#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
t() { local s=$(date +%s); "$@" >/dev/null 2>&1; echo $(( $(date +%s) - s )); }
test_s=$(t make test)
replay_s=$(t make replay)
validate_s=$(t make validate)
printf '{\n "measured_on": "%s",\n "make_test_s": %s,\n "make_replay_s": %s,\n "make_validate_s": %s,\n "machine": "%s"\n}\n' \
  "$(TZ=America/Phoenix date +%Y-%m-%d)" "$test_s" "$replay_s" "$validate_s" "$(uname -s | sed s/Darwin/macOS/) $(uname -m) with Docker images already built" > report/timings.json
cat report/timings.json
