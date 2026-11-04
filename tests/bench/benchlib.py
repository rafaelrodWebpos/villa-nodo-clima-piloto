"""Ayudantes comunes del nivel bench: protocolo de tres fases (panel + evidencia)
y captura de arranque (P-BOOT-CAPTURE). Los usan los JRN y los TC."""
import contextlib
import pathlib
import re
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
PASSED = set()          # pasos del recorrido que han pasado en esta sesión


# --------------------------------------------------------------------------
# Ayudantes
# --------------------------------------------------------------------------
class Case:
    """Panel del banco + evidencia markdown de un paso (protocolo de tres fases)."""

    def __init__(self, tb, tid, name, run_dir):
        self.tb, self.tid, self.name, self.run_dir = tb, tid, name, run_dir
        self.lines = [f"# {tid} — {name}", ""]
        self.result, self.detail = "FAIL", ""

    def step(self, text):
        self.tb.test_step(self.tid, self.name, text)   # antes de la acción, nunca después
        self.lines += [f"- {text}"]

    def note(self, *text):
        self.lines += list(text)

    def save_log(self, suffix, lines):
        (self.run_dir / f"{self.tid}-{suffix}.log").write_text("\n".join(lines) + "\n")
        self.lines += [f"- log: `{self.tid}-{suffix}.log` ({len(lines)} líneas)"]

    def passed(self, detail):
        self.result, self.detail = "PASS", detail
        PASSED.add(self.tid)


@contextlib.contextmanager
def case(tb, tid, name, run_dir, requires=None, spec="JRN-01 villa-nodo-clima-piloto"):
    c = Case(tb, tid, name, run_dir)
    tb.test_start(spec, "Fase 1", total=1)
    try:
        if requires and requires not in PASSED:
            pytest.skip(f"not done: {requires} no ha pasado en esta sesión (workflow)")
        yield c
    except pytest.skip.Exception as e:
        c.result, c.detail = "SKIP", str(e)
        raise
    except Exception as e:
        c.detail = f"{type(e).__name__}: {e}"
        raise
    finally:
        tb.test_result(tid, name, c.result, c.detail[:200])
        tb.test_end()
        c.lines += ["", f"**Resultado: {c.result}** — {c.detail}", ""]
        (run_dir / f"{tid}.md").write_text("\n".join(c.lines))


def _parse_flash_args(coldflash: pathlib.Path) -> dict:
    """{offset: ruta} de coldflash/flash_args (líneas «0x... fichero»).

    flash_args nombra cada imagen con su ruta en build/ (p. ej.
    bootloader/bootloader.bin); build.yml las copia planas a coldflash/."""
    images = {}
    for line in (coldflash / "flash_args").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].startswith("0x"):
            f = coldflash / pathlib.PurePosixPath(parts[1]).name
            assert f.is_file(), f"{parts[1]} de flash_args no está en coldflash/"
            images[parts[0]] = str(f)
    assert images, "flash_args sin imágenes"
    return images


def _nvs_partition() -> tuple:
    """(offset, tamaño) de la partición nvs, de partitions.csv (FSD §2.2)."""
    for line in (REPO / "partitions.csv").read_text().splitlines():
        cols = [c.strip() for c in line.split(",")]
        if cols and cols[0] == "nvs":
            return cols[3], int(cols[4], 16)
    raise AssertionError("partitions.csv sin partición nvs")


def _lines(resp: dict) -> list:
    out = resp.get("output") or resp.get("lines") or []
    return [o.get("text", "") if isinstance(o, dict) else str(o) for o in out]


def _after_last_reset(lines: list) -> list:
    """Solo lo que el DUT escribió tras su último «rst:» de ROM: la respuesta
    del reset puede traer antes la cola del arranque anterior."""
    idx = [i for i, ln in enumerate(lines) if ln.startswith("rst:")]
    return lines[idx[-1]:] if idx else []


def _boot_capture(tb, slot: str, pattern: str) -> list:
    """P-BOOT-CAPTURE: el reset trae su propio log; si el patrón no está,
    monitor esperando (15 s) y segundo reset."""
    first = tb.serial_reset(slot)
    assert first.get("method") != "jtag", "el reset fue por JTAG: la respuesta es de OpenOCD, no del DUT"
    lines = _lines(first)
    if any(pattern in ln for ln in _after_last_reset(lines)):
        return lines
    seen = {}
    mon = threading.Thread(target=lambda: seen.update(tb.serial_monitor(slot, pattern=pattern, timeout=15)))
    mon.start()
    time.sleep(1)  # el monitor tiene que estar esperando antes del reset
    second = tb.serial_reset(slot)
    mon.join(25)
    return lines + _lines(second) + _lines(seen)


def _boot_ids(lines: list) -> list:
    """<nodo> de cada línea E1 «boot: <nodo> fw=…» (FSD §18)."""
    return [m.group(1) for ln in lines for m in [re.search(r"boot: (\S+) fw=", ln)] if m]


