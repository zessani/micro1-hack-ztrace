FROM zbench-base
COPY repo/ /work/repo/
RUN cd /work/repo \
    && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1 \
    && npm rebuild sqlite3 >/dev/null 2>&1 \
    && test -f node_modules/sqlite3/build/Release/node_sqlite3.node \
    && mkdir -p temp \
    && git init -q -b main && git config user.email bench@zbench.local && git config user.name zbench \
    && git add -A && git add -f ormconfig.json && git commit -q -m "Initial commit" \
    && chown -R agent:agent /work/repo
USER agent
WORKDIR /work/repo
