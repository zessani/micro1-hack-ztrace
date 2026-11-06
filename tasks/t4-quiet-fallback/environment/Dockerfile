FROM zbench-base
COPY fastcsv-src/ /tmp/fastcsv-src/
COPY repo/ /work/repo/
RUN mkdir -p /work/repo/vendor \
    && /opt/venv/bin/pip install --no-cache-dir pytest==8.3.3 setuptools wheel \
    && cd /tmp/fastcsv-src && /opt/venv/bin/python setup.py -q sdist -d /work/repo/vendor \
    && /opt/venv/bin/pip download --no-cache-dir -d /work/repo/vendor setuptools wheel \
    && /opt/venv/bin/pip uninstall -y setuptools wheel \
    && rm -rf /tmp/fastcsv-src \
    && printf '[global]\nno-index = true\nfind-links = /work/repo/vendor\n' > /etc/pip.conf \
    && cd /work/repo \
    && git init -q -b main && git config user.email bench@zbench.local && git config user.name zbench \
    && git add -A && git commit -q -m "Initial commit" \
    && chown -R agent:agent /work/repo
USER agent
WORKDIR /work/repo
