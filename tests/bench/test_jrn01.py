"""JRN-01 — el recorrido ordinario (testing/test-plan.yaml → tests).

Workflow: los pasos se ejecutan en orden y cada uno parte del estado que deja
el anterior. El fichero es el orden; pytest los recorre de arriba abajo, y un
paso cuyo anterior no pasó queda en not done (skip), nunca en failed.
"""
import contextlib
import pathlib
import re
import threading
import time

import pytest

pytestmark = pytest.mark.journey
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
def case(tb, tid, name, run_dir, requires=None):
    c = Case(tb, tid, name, run_dir)
    tb.test_start("JRN-01 villa-nodo-clima-piloto", "Fase 1", total=1)
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


# --------------------------------------------------------------------------
# JRN-01.0 · C-HW-02
# --------------------------------------------------------------------------
def test_jrn_01_0_flash_ci_image(testbench, dut_slot, firmware, boot_marker,
                                 bench_image_marker, commit_under_test, run_dir, tmp_path):
    """JRN-01.0 · C-HW-02 — la imagen de la CI arranca en SLOT1 con la NVS borrada; el marcador de banco, según la variante."""
    tb = testbench
    with case(tb, "JRN-01.0", "Grabar la imagen de la CI", run_dir) as c:
        c.note(f"- commit bajo prueba: `{commit_under_test}`",
               f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})",
               f"- slot: {dut_slot}", "")
        # Precondiciones
        c.step("Precondiciones: slot presente")
        slot = tb.get_slot(dut_slot)
        if not slot.get("present"):
            pytest.skip(f"not done: {dut_slot} no presente (state {slot.get('state')})")

        # Ejecución: flasheo con los offsets de flash_args + NVS en blanco (P-NVS-ERASE)
        images = _parse_flash_args(firmware["dir"] / "coldflash")
        nvs_off, nvs_size = _nvs_partition()
        assert nvs_off not in images, "flash_args ya escribe en la NVS"
        blank = tmp_path / "nvs_blank.bin"
        blank.write_bytes(b"\xff" * nvs_size)
        images[nvs_off] = str(blank)
        c.note("", "## Flasheo", "", *[f"- `{o}` {pathlib.Path(p).name}"
               for o, p in sorted(images.items(), key=lambda kv: int(kv[0], 16))], "")
        c.step(f"Grabando {len(images)} imágenes en {dut_slot} (NVS en blanco)")
        res = tb.flash(dut_slot, images, chip="esp32s3")
        c.note(f"- respuesta: ok={res.get('ok')} returncode={res.get('returncode')}", "")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"

        # Ejecución: captura del arranque (P-BOOT-CAPTURE)
        c.step(f"Reset y captura del arranque: {bench_image_marker}, {boot_marker}")
        lines = _boot_capture(tb, dut_slot, boot_marker)
        c.note("", "## Arranque", "")
        c.save_log("boot", lines)

        # Resultado
        boot = _after_last_reset(lines)
        assert boot, "la captura no contiene ninguna línea rst: (el reset no se vio)"
        has_marker = any(bench_image_marker in ln for ln in boot)
        has_init = any(boot_marker in ln for ln in boot)
        ver = next((ln for ln in boot if re.search(r"nodo_clima \S+", ln)), "")
        c.note(f"- tras el último `rst:` ({len(boot)} líneas):",
               f"- `{bench_image_marker}`: {'sí' if has_marker else 'NO'}",
               f"- `{boot_marker}`: {'sí' if has_init else 'NO'}",
               f"- versión en el log: `{ver.strip()}`")
        if firmware["variant"] == "bench":
            assert has_marker, f"{bench_image_marker} no aparece en el arranque de la imagen de banco"
        else:  # verify: imagen de producción del tag (release_verify en el plan)
            assert not has_marker, f"{bench_image_marker} aparece en la imagen de producción (C-LOG-01)"
        assert has_init, f"«{boot_marker}» no aparece en el arranque"
        assert firmware["version"] in ver, f"el log no muestra la versión {firmware['version']}"
        mk = bench_image_marker if firmware["variant"] == "bench" else f"sin {bench_image_marker}"
        c.passed(f"{firmware['version']} arranca: {mk} + {boot_marker}")


# --------------------------------------------------------------------------
# JRN-01.1 · T02, FR-POR-01, FR-ID-01
# --------------------------------------------------------------------------
PORTAL_LIMIT_S = 10          # T02 / FR-POR-01 (D21)
ID_RESETS = 3                # FR-ID-01 (bench): 3 reinicios


def test_jrn_01_1_portal_without_config(testbench, dut_slot, dut_mac, run_dir):
    """JRN-01.1 — sin configuración: ARRANQUE -> PORTAL y AP abierto clima-xxxxxx en ≤ 10 s; id estable en 3 reinicios."""
    tb = testbench
    expected_id = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "JRN-01.1", "Portal sin configuración", run_dir, requires="JRN-01.0") as c:
        c.note(f"- slot: {dut_slot}; id esperado (FR-ID-01, MAC de dut.identity): `{expected_id}`", "")
        # Precondiciones: la NVS la dejó en blanco JRN-01.0; la radio del banco, libre para escanear
        c.step("Precondiciones: AP del banco apagado (el escaneo comparte la radio)")
        assert not tb.ap_status().get("active"), \
            "el AP del banco está activo: el escaneo no puede correr (no se apaga aquí: no es nuestro)"

        # Ejecución 1: reset y escaneo en paralelo hasta ver el SSID del nodo
        c.step(f"Reset y escaneo hasta ver {expected_id} (≤ {PORTAL_LIMIT_S} s)")
        reset_out = {}
        t0 = time.time()
        rt = threading.Thread(target=lambda: reset_out.update(tb.serial_reset(dut_slot)))
        rt.start()
        # Un escaneo lanzado a la vez que el reset barre el canal antes de que
        # exista el AP (el DUT lo levanta ~0,6 s tras su rst:). Esperar al
        # buffer del banco tampoco sirve: va segundos por detrás. Se escanea
        # desde t0 + 1 s; el tiempo se mide desde t0 (cota superior).
        time.sleep(1.0)
        found, scans = None, []
        while time.time() - t0 < PORTAL_LIMIT_S + 10:
            nets = tb.scan().get("networks") or []
            t_scan = time.time() - t0
            mine = [n for n in nets if n.get("ssid") == expected_id]
            others = [n for n in nets if str(n.get("ssid", "")).startswith("clima-") and n.get("ssid") != expected_id]
            scans.append((round(t_scan, 1), [(n["ssid"], n["auth"]) for n in mine + others]))
            if mine:
                found = (t_scan, mine[0])
                break
        rt.join(30)
        c.note("", "## Escaneos (solo SSID clima-*)", "", *[f"- t={t} s: {v or 'ninguno'}" for t, v in scans], "")

        # Ejecución 2: log del arranque (respuesta del reset + buffer del slot desde t0)
        buf = tb.serial_output(dut_slot, lines=300, since=t0)
        lines = _lines(reset_out) + ["--- buffer del slot ---"] + _lines(buf)
        c.save_log("boot", lines)
        boot = _after_last_reset(_lines(reset_out)) + _lines(buf)

        # Resultado 1 — T02 y FR-POR-01
        assert found, f"{expected_id} no apareció en {len(scans)} escaneos ({PORTAL_LIMIT_S + 10} s)"
        t_found, net = found
        c.note(f"- `{expected_id}` visto a los {t_found:.1f} s (cota superior desde la petición de reset), auth {net['auth']}")
        assert net["auth"] == "OPEN", f"el AP del portal tiene seguridad {net['auth']} (FR-POR-01: abierto)"
        assert t_found <= PORTAL_LIMIT_S, f"SSID a los {t_found:.1f} s > {PORTAL_LIMIT_S} s (T02/FR-POR-01)"
        con_ln = next((ln for ln in boot if "con: ARRANQUE -> PORTAL (fin_arranque)" in ln), None)
        boot_ln = next((ln for ln in boot if re.search(r"boot: \S+ fw=", ln)), None)
        assert con_ln, "falta «con: ARRANQUE -> PORTAL (fin_arranque)» en el log (T02, E0)"
        assert boot_ln, "falta la línea boot: (E1)"
        # T02: el límite se mide desde la línea boot: (FSD §6.6), en el reloj del DUT («I (<ms>)»)
        ms = lambda ln: int(re.match(r"\w \((\d+)\)", ln).group(1))
        t02_ms = ms(con_ln) - ms(boot_ln)
        c.note(f"- T02 en el reloj del DUT: boot: → con: en {t02_ms} ms (límite {PORTAL_LIMIT_S * 1000} ms)")
        assert 0 <= t02_ms <= PORTAL_LIMIT_S * 1000, f"T02 en {t02_ms} ms > {PORTAL_LIMIT_S} s"
        assert not any("wifi: intento" in ln for ln in boot), "T02 prohíbe intentar el STA: hay «wifi: intento»"
        ids = _boot_ids(boot)[:1]   # respuesta del reset y buffer se solapan: un arranque, un id
        assert ids and ids[0] == expected_id, f"boot: muestra {ids[:1]} en lugar de {expected_id} (FR-ID-01)"

        # Ejecución 3 — FR-ID-01 (bench): el id no cambia en 3 reinicios
        for i in range(2, ID_RESETS + 1):
            c.step(f"FR-ID-01: reinicio {i} de {ID_RESETS}")
            lines_i = _boot_capture(tb, dut_slot, "con: ARRANQUE -> PORTAL")
            c.save_log(f"boot{i}", lines_i)
            ids += _boot_ids(_after_last_reset(lines_i))[:1]
        c.note(f"- ids en {ID_RESETS} arranques: {ids}")
        assert len(ids) == ID_RESETS and set(ids) == {expected_id}, f"id inestable o ausente: {ids} (FR-ID-01)"
        c.passed(f"PORTAL en {t_found:.1f} s, {expected_id} abierto, id estable en {ID_RESETS} arranques")
