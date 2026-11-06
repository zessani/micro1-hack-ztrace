#!/bin/bash
set -e
export PATH=/opt/venv/bin:$PATH
cd /work/repo
sed -i 's/    pa, pb = str(Version(a)), str(Version(b))/    pa, pb = Version(a).parts, Version(b).parts/' pkgver/version.py
pytest
