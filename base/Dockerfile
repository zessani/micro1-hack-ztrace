FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      strace git ca-certificates curl python3 python3-venv python3-dev build-essential xz-utils \
    && rm -rf /var/lib/apt/lists/*
ARG NODE_VERSION=22.11.0
RUN arch=$(dpkg --print-architecture | sed 's/amd64/x64/') \
    && curl -fsSL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${arch}.tar.xz \
       | tar -xJ -C /usr/local --strip-components=1
RUN userdel -r ubuntu 2>/dev/null || true \
    && useradd -m -u 1000 -s /bin/bash agent \
    && python3 -m venv /opt/venv && chown -R agent:agent /opt/venv \
    && mkdir -p /work /trace /opt/zbench && chown agent:agent /work && chmod 700 /trace
ENV PATH=/opt/venv/bin:$PATH
WORKDIR /work/repo
