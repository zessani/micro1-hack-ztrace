#!/bin/bash
set -eu
here=$(cd "$(dirname "$0")" && pwd)
tracer=$(dirname "$here")
image=${IMAGE:-zbench-base}

gen() {
    local name=$1
    shift
    local out="$here/$name"
    rm -rf "$out"
    mkdir -p "$out"
    docker run --rm --cap-add SYS_PTRACE --security-opt seccomp=unconfined \
        -v "$tracer:/opt/zbench/tracer:ro" -v "$out:/out" "$image" bash -c '
            mkdir -p /work/repo/sub/deeper && chown -R agent:agent /work/repo
            cd /work/repo
            /opt/zbench/tracer/ztrace-run "$@"
            echo "exit=$?" > /out/exit
            cp /trace/trace.log /trace/ztrace.meta /out/
        ' gen "$@"
    gzip -9 -f "$out/trace.log"
}

gen fake_agent -- node /opt/zbench/tracer/fixtures/scripts/fake_agent.js
gen solve --root-is-command -- /opt/zbench/tracer/fixtures/scripts/solve.sh
gen dns --root-is-command -- python3 /opt/zbench/tracer/fixtures/scripts/dns.py
