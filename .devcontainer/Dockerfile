# Un proyecto, un contenedor: toolchain, nivel bench y el runner del job
# release-verify (docs/Method/project/arquitectura.md).
FROM espressif/idf:v6.0.2

ARG DEBIAN_FRONTEND=noninteractive
ARG RUNNER_VERSION=2.337.0
ARG RUNNER_SHA256=70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates jq gh sudo python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Nivel bench (pytest). Venv propio, separado del Python de ESP-IDF (que solo
# existe tras export.sh).
COPY tests/bench/requirements.txt /tmp/bench-requirements.txt
RUN python3 -m venv /opt/bench-venv \
    && /opt/bench-venv/bin/pip install --no-cache-dir -r /tmp/bench-requirements.txt

# TestbenchDriver (capacidad bench-driver del plan): pytest/testbench_driver.py
# del repo del testbench, fijado a un commit y a su sha256. Solo usa la
# biblioteca estándar. Cambiar de commit = cambiar las dos líneas a la vez.
ARG TESTBENCH_REPO=SensorsIot/Embedded-AI-Harness
ARG TESTBENCH_COMMIT=db6a0933075bb9ff5a99bb8e307a54b6a01af57d
ARG TESTBENCH_DRIVER_SHA256=8ed154118de9d0130d7ac3a25a1c32d550bd832e3b09c5961fca2a85414691bb
RUN site=$(/opt/bench-venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])') \
    && curl -sSfL -o "$site/testbench_driver.py" \
       "https://raw.githubusercontent.com/${TESTBENCH_REPO}/${TESTBENCH_COMMIT}/pytest/testbench_driver.py" \
    && echo "${TESTBENCH_DRIVER_SHA256}  $site/testbench_driver.py" | sha256sum -c - \
    && echo "${TESTBENCH_COMMIT}" > /opt/bench-venv/TESTBENCH_COMMIT
# El entrypoint de IDF antepone su propio Python: el nivel bench se invoca
# siempre como /opt/bench-venv/bin/python.

# El runner se niega a ejecutarse como root: usuario propio.
RUN useradd -m -s /bin/bash runner \
    && mkdir -p /opt/actions-runner && cd /opt/actions-runner \
    && curl -sSfL -o runner.tgz \
       "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz" \
    && echo "${RUNNER_SHA256}  runner.tgz" | sha256sum -c - \
    && tar xzf runner.tgz && rm runner.tgz \
    && ./bin/installdependencies.sh \
    && chown -R runner:runner /opt/actions-runner
