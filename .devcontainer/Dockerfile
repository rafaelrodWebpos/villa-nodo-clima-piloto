# Un proyecto, un contenedor: toolchain, nivel bench y el runner del job
# release-verify (docs/Method/project/arquitectura.md).
# SEC-08: imagen base por digest (la etiqueta es mutable)
FROM espressif/idf:v6.0.2@sha256:0d8c9773d48a327233f9c1d7c654ff0bcf133ae24503ea2e97a57cfe02b8cb67

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
    && /opt/bench-venv/bin/pip install --no-cache-dir --require-hashes -r /tmp/bench-requirements.txt

# TestbenchDriver (capacidad bench-driver del plan): pytest/testbench_driver.py
# del repo del testbench, fijado a un commit y a su sha256. Solo usa la
# biblioteca estándar. Cambiar de commit = cambiar las dos líneas a la vez.
# Fork villa-2 (H-87): el driver del fork, que envía el token X-Harness-Token
# (TESTBENCH_TOKEN del .env) y trae los métodos de las capacidades nuevas.
ARG TESTBENCH_REPO=rafaelrodWebpos/Embedded-AI-Harness
ARG TESTBENCH_COMMIT=bb1ec0e43863747ef68e56cc7287806ad4f47df2
ARG TESTBENCH_DRIVER_SHA256=efef06678417f299bd7d4cb8ca5636bd5b06d1201de47ff69fa639d7cb76406f
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
