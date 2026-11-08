FROM zbench-base
COPY repo/ /work/repo/
RUN mkdir -p /work/repo/vendor \
    && /opt/venv/bin/pip install --no-cache-dir pytest==8.3.3 \
    && /opt/venv/bin/pip download --no-cache-dir --no-binary :all: --no-deps -d /work/repo/vendor MarkupSafe==2.1.5 \
    && /opt/venv/bin/pip download --no-cache-dir -d /work/repo/vendor setuptools wheel \
    && printf '[global]\nno-index = true\nfind-links = /work/repo/vendor\n' > /etc/pip.conf \
    && rm -f /usr/include/python3*/Python.h /usr/include/*/python3*/pyconfig.h \
    && cd /work/repo && mkdir -p data && python3 scripts/seed_dev.py \
    && git init -q -b main && git config user.email bench@zbench.local && git config user.name zbench \
    && git add -A && git commit -q -m "Initial commit" \
    && chown -R agent:agent /work/repo
USER agent
WORKDIR /work/repo
