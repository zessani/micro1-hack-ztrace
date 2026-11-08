#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
out=dist/ztrace-bench.zip
mkdir -p dist
rm -f "$out"
git diff --quiet HEAD || { echo "make zip: uncommitted changes; commit first so the zip matches a commit" >&2; exit 1; }
git archive --format=zip -9 --prefix=ztrace-bench/ -o "$out" HEAD
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
unzip -q "$out" -d "$tmp"
if grep -rIl -e 'sk-''ant-' -e 'sk-''or-' "$tmp" >/dev/null; then
  echo "make zip: key prefix found:" >&2; grep -rIl -e 'sk-''ant-' -e 'sk-''or-' "$tmp" >&2; exit 1
fi
if [ -f .env ]; then
  while IFS='=' read -r k v; do
    [ -z "${v:-}" ] && continue
    case "$k" in \#*|"") continue;; esac
    if grep -rIlF -e "$v" "$tmp" >/dev/null; then echo "make zip: value of $k found in zip" >&2; exit 1; fi
  done < .env
fi
for bad in .env results/*/*/*/raw; do
  if compgen -G "$tmp/ztrace-bench/$bad" >/dev/null; then echo "make zip: $bad present" >&2; exit 1; fi
done
size=$(wc -c < "$out")
[ "$size" -lt 52428800 ] || { echo "make zip: $size bytes exceeds 50 MB" >&2; exit 1; }
echo "make zip: $out $(du -h "$out" | cut -f1), commit $(git rev-parse --short HEAD), no secrets found"
