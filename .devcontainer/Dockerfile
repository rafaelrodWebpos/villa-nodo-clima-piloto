# Un proyecto, un contenedor: toolchain, nivel bench y el runner del job
# release-verify (docs/Method/project/arquitectura.md).
FROM espressif/idf:v6.0.2

ARG RUNNER_VERSION=2.337.0
ARG RUNNER_SHA256=70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates jq gh sudo \
    && rm -rf /var/lib/apt/lists/*

# Nivel bench (pytest). TestbenchDriver se instala en /commission, cuando el
# banco exista (testing/test-plan.yaml, capacidad bench-driver).
COPY tests/bench/requirements.txt /tmp/bench-requirements.txt
RUN PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --no-cache-dir -r /tmp/bench-requirements.txt

# El runner se niega a ejecutarse como root: usuario propio.
RUN useradd -m -s /bin/bash runner \
    && mkdir -p /opt/actions-runner && cd /opt/actions-runner \
    && curl -sSfL -o runner.tgz \
       "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
    && echo "${RUNNER_SHA256}  runner.tgz" | sha256sum -c - \
    && tar xzf runner.tgz && rm runner.tgz \
    && ./bin/installdependencies.sh \
    && chown -R runner:runner /opt/actions-runner
