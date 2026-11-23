"""Hook H-62 (.claude/hooks/limite-espera.py): esperas en segundo plano. Decisión del propietario
(2026-11-23): espera larga de hasta 93600 s solo con `timeout N docker wait <c>` o
`timeout N bash -c 'while kill -0 <pid>; do sleep 60; done'`; cualquier otra espera, 600 s como
mucho. Corre con `python3 tests/host/test_limite_espera.py`."""
import json
import pathlib
import subprocess
import sys
import unittest

HOOK = pathlib.Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "limite-espera.py"


def decide(cmd, fondo=True):
    datos = {"tool_name": "Bash", "tool_input": {"command": cmd, "run_in_background": fondo}}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(datos), capture_output=True,
                       text=True, check=True)
    if not r.stdout.strip():
        return "allow"
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]


PASAN = [
    "timeout 93600 docker wait nodo-24h",
    "timeout 14400 bash -c 'while kill -0 381956 2>/dev/null; do sleep 60; done'",
    "timeout 14400 bash -c 'while kill -0 381956; do sleep 60; done'; date '+%T'",
    "timeout 600 bash -c 'until curl -s x; do sleep 5; done'",
    "timeout 590 flock -w 580 /tmp/l true; echo rc=$?",
    "timeout 590 tail --pid=123 -f /dev/null",
    "timeout 10m bash -c 'while true; do sleep 1; done'",
    "make build",
]
BLOQUEADAS = [
    "while kill -0 381956; do sleep 60; done",                                  # sin timeout
    "timeout 93601 docker wait nodo-24h",                                       # más de 26 h
    "timeout 93601 bash -c 'while kill -0 1; do sleep 60; done'",
    "timeout 14400 bash -c 'while kill -0 1; do sleep 30; done'",               # otro sleep
    "timeout 14400 bash -c 'until curl -s x; do sleep 60; done'",               # otro bucle
    "timeout 14400 bash -c 'while kill -0 1; do sleep 60; done; sleep 9999'",   # algo más dentro
    "timeout 14400 tail --pid=123 -f /dev/null",                                # otra forma de esperar
    "docker wait nodo-24h",                                                     # sin timeout
    "timeout 93600 docker wait c; while true; do sleep 5; done",                # otra espera sin límite
    "timeout 93600 docker wait c; timeout 900 bash -c 'while true; do sleep 5; done'",
    "timeout 700 bash -c 'until curl -s x; do sleep 5; done'",
    "gh run list " + "-c abc1234",                                              # hash corto (regla 2)
]


class TestH62(unittest.TestCase):
    def test_pasan(self):
        for c in PASAN:
            self.assertEqual(decide(c), "allow", c)

    def test_bloqueadas(self):
        for c in BLOQUEADAS:
            self.assertEqual(decide(c), "deny", c)

    def test_primer_plano_no_se_juzga_como_espera(self):
        self.assertEqual(decide("while kill -0 1; do sleep 60; done", fondo=False), "allow")


if __name__ == "__main__":
    unittest.main(verbosity=1)
