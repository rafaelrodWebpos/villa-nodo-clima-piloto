"""Nivel bench — fixtures compartidas (testing/test-plan.yaml, docs/Method/standards/testing.md).

Se ejecuta con el Python del devcontainer:
    /opt/bench-venv/bin/python -m pytest tests/bench -m journey [--firmware-dir DIR]

- El banco se lee de TESTBENCH_URL (.env, nunca versionado).
- El slot del DUT sale de `dut.slot` del plan: un solo hogar por hecho.
- Sin --firmware-dir, el firmware se pide a la CI sobre el commit bajo prueba
  (procedure de JRN-01.0); necesita `gh` autenticado (GH_TOKEN).
"""
import datetime
import json
import os
import pathlib
import re
import subprocess
import time

import pytest
from testbench_driver import TestbenchDriver

REPO = pathlib.Path(__file__).resolve().parents[2]
PLAN = REPO / "testing" / "test-plan.yaml"
GH_REPO = "rafaelrodWebpos/villa-nodo-clima-piloto"


def pytest_addoption(parser):
    parser.addoption("--firmware-dir", default=None,
                     help="artefacto de build.yml ya descargado (coldflash/ + firmware_v*.bin)")
    parser.addoption("--ci-variant", default="bench", choices=["bench", "production"],
                     help="variante que se pide a la CI si no hay --firmware-dir")


def pytest_configure(config):
    config.addinivalue_line("markers", "journey: paso del recorrido estándar (JRN-*), en orden")


def _plan_scalar(section: str, key: str) -> str:
    """Lee `section.key` del plan sin depender de PyYAML (no está en el venv)."""
    text = PLAN.read_text(encoding="utf-8")
    block = re.search(rf"^{section}:\n((?:[ #].*\n|\n)+)", text, re.M)
    assert block, f"{section} no está en el plan"
    m = re.search(rf'^  {key}:\s*(?:"([^"]*)"|(\S+))', block.group(1), re.M)
    assert m, f"{section}.{key} no está en el plan"
    return m.group(1) if m.group(1) is not None else m.group(2)


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _gh(*args) -> str:
    return subprocess.run(["gh", *args, "-R", GH_REPO], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture(scope="session")
def testbench():
    url = os.environ.get("TESTBENCH_URL")
    if not url:
        pytest.skip("not done: TESTBENCH_URL no definido (precondición)")
    tb = TestbenchDriver(url)
    try:
        tb.info()
    except Exception as e:  # banco apagado = precondición, no fallo del firmware
        pytest.skip(f"not done: banco no alcanzable ({type(e).__name__})")
    return tb


@pytest.fixture(scope="session")
def dut_slot():
    return _plan_scalar("dut", "slot")


@pytest.fixture(scope="session")
def dut_mac():
    """MAC de la unidad del banco, leída de dut.identity (publicada, H-20)."""
    m = re.search(r"^  identity:.*\n(?:    .*\n)*?    mac: (\S+)", PLAN.read_text(encoding="utf-8"), re.M)
    assert m, "dut.identity.mac no está en el plan"
    return m.group(1)


@pytest.fixture(scope="session")
def boot_marker():
    return _plan_scalar("dut", "boot_marker")


@pytest.fixture(scope="session")
def bench_image_marker():
    return _plan_scalar("dut", "bench_image_marker")


@pytest.fixture(scope="session")
def commit_under_test():
    return _git("rev-parse", "HEAD")


@pytest.fixture(scope="session")
def run_dir(commit_under_test):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = REPO / "test-results" / f"{stamp}-{commit_under_test[:7]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture(scope="session")
def firmware(request, commit_under_test, tmp_path_factory):
    """Devuelve {dir, version, variant, ci_run}; dir contiene coldflash/flash_args."""
    given = request.config.getoption("--firmware-dir")
    if given:
        d = pathlib.Path(given).resolve()
        ci_run = os.environ.get("GITHUB_RUN_ID")
    else:
        variant = request.config.getoption("--ci-variant")
        # La CI construye lo que hay en GitHub: el commit bajo prueba tiene que estar subido.
        if _git("status", "--porcelain", "--untracked-files=no"):
            pytest.skip("not done: hay cambios sin commit; la CI no construiría lo que se prueba")
        remote = _git("ls-remote", "origin", "refs/heads/main").split()[0]
        if remote != commit_under_test:
            pytest.skip("not done: HEAD no es origin/main; sube el commit antes de pedir el build")
        # La versión lleva el commit: el log del arranque prueba qué commit corre en la placa
        ver_ci = f"0.0.0-{commit_under_test[:7]}"
        since = time.time() - 5
        _gh("workflow", "run", "build.yml", "--ref", "main",
            "-f", f"variant={variant}", "-f", f"version={ver_ci}")
        ci_run = None
        for _ in range(60):  # workflow_dispatch no devuelve el id: se busca el run nuevo
            time.sleep(3)
            runs = json.loads(_gh("run", "list", "-w", "build.yml", "-e", "workflow_dispatch",
                                  "-L", "5", "--json", "databaseId,headSha,createdAt"))
            for r in runs:
                created = datetime.datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
                if r["headSha"] == commit_under_test and created.timestamp() >= since:
                    ci_run = str(r["databaseId"])
                    break
            if ci_run:
                break
        assert ci_run, "la CI no creó el run del workflow_dispatch en 180 s"
        subprocess.run(["gh", "run", "watch", ci_run, "--exit-status", "-R", GH_REPO],
                       check=True, capture_output=True)
        d = tmp_path_factory.mktemp("fw")
        name = f"firmware-v{ver_ci}-{variant}" if variant != "production" else f"firmware-v{ver_ci}"
        _gh("run", "download", ci_run, "-n", name, "-D", str(d))
    bins = sorted(d.glob("firmware_v*.bin"))
    assert len(bins) == 1 and (d / "coldflash" / "flash_args").is_file(), \
        f"artefacto incompleto en {d}: {[p.name for p in d.iterdir()]}"
    version = bins[0].stem[len("firmware_v"):]
    # commit: el que la versión tiene que nombrar (None con --firmware-dir: la del tag)
    return {"dir": d, "version": version,
            "variant": "bench" if version.endswith("-bench") else "production",
            "ci_run": ci_run, "commit": None if given else commit_under_test[:7]}
