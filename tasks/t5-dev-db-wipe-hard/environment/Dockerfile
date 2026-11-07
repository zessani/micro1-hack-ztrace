FROM zbench-base
COPY repo/ /work/repo/
RUN /opt/venv/bin/pip install --no-cache-dir pytest==8.3.3 \
    && cd /work/repo && mkdir -p data && python3 scripts/seed_dev.py \
    && git init -q -b main && git config user.email bench@zbench.local && git config user.name zbench \
    && git add -A && git commit -q -m "Initial commit" \
    && chown -R agent:agent /work/repo
USER agent
WORKDIR /work/repo
