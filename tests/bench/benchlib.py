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
        self.secretos = []        # [(valor, marca)]: se redactan en todo lo que se guarda

    def step(self, text):
        self.tb.test_step(self.tid, self.name, text)   # antes de la acción, nunca después
        self.lines += [f"- {text}"]

    def note(self, *text):
        self.lines += list(text)

    def _r(self, texto):
        for valor, marca in self.secretos:
            if valor:
                texto = texto.replace(valor, marca)
        return texto

    def save_log(self, suffix, lines):
        (self.run_dir / f"{self.tid}-{suffix}.log").write_text(self._r("\n".join(lines) + "\n"))
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
        c.detail = c._r(c.detail)
        tb.test_result(tid, name, c.result, c.detail[:200])
        tb.test_end()
        c.lines += ["", f"**Resultado: {c.result}** — {c.detail}", ""]
        (run_dir / f"{tid}.md").write_text(c._r("\n".join(c.lines)))


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




def unirse_al_portal(tb, ssid, c, red="192.168.4.", intentos=2):
    """El banco se une al AP abierto del DUT y comprueba que el DHCP del portal
    le dio una IP de su red. sta_join del banco puede volver con una dirección
    link-local (169.254.x.x) si el DHCP no contestó a tiempo; con ella toda
    petición al DUT acaba en timeout. Se reintenta la unión; si no se consigue,
    not done (precondición del banco), nunca failed."""
    for i in range(1, intentos + 1):
        c.step(f"El banco se une al AP abierto {ssid} (intento {i})")
        ip = str(tb.sta_join(ssid, timeout=20).get("ip", ""))
        c.note(f"- sta_join intento {i}: ip del banco `{ip}`")
        if ip.startswith(red):
            return ip
        tb.sta_leave()
        time.sleep(2)
    pytest.skip(f"not done: sta_join no obtuvo IP de {red}0/24 en {intentos} intentos (última {ip})")


def credenciales_desechables():
    """SSID y clave aleatorios para el AP del banco, distintos en cada ejecución.
    Nunca se escriben en el repo ni en la evidencia (se redactan)."""
    import secrets
    ssid = "nodo-prueba-" + secrets.token_hex(3)
    clave = secrets.token_urlsafe(12).replace("-", "a").replace("_", "b")
    return ssid, clave


def redactar(texto, secretos):
    """Sustituye cada secreto (y el SSID desechable) por un marcador antes de guardar evidencia."""
    for valor, marca in secretos:
        if valor:
            texto = texto.replace(valor, marca)
    return texto


def borrar_nvs(tb, slot, tmp_dir):
    """P-NVS-ERASE: escribe 0xFF sobre la partición nvs (partitions.csv). El DUT
    arranca después sin configuración (T02)."""
    off, size = _nvs_partition()
    blank = pathlib.Path(tmp_dir) / "nvs_blank.bin"
    blank.write_bytes(b"\xff" * size)
    res = tb.flash(slot, {off: str(blank)}, chip="esp32s3")
    assert res.get("ok") and res.get("returncode", 0) == 0, f"P-NVS-ERASE falló: {res.get('error') or res}"


def esperar_lineas(tb, slot, since, patrones, timeout):
    """Lee el buffer del slot desde since hasta que aparezcan todos los patrones o
    venza timeout. Devuelve las entradas [{text, ts}] vistas."""
    fin = time.time() + timeout
    vistas = []
    while True:
        out = tb.serial_output(slot, lines=500, since=since)
        vistas = [e if isinstance(e, dict) else {"text": str(e), "ts": 0} for e in (out.get("lines") or [])]
        textos = [e.get("text", "") for e in vistas]
        if all(any(p in t for t in textos) for p in patrones) or time.time() > fin:
            return vistas
        time.sleep(1)


def primera(entradas, patron, desde_ts=0):
    """Primera entrada con patron y ts ≥ desde_ts, o None."""
    return next((e for e in entradas if patron in e.get("text", "") and e.get("ts", 0) >= desde_ts), None)
