"""JRN-01 — el recorrido ordinario (testing/test-plan.yaml → tests).

Workflow: los pasos se ejecutan en orden y cada uno parte del estado que deja
el anterior. El fichero es el orden; pytest los recorre de arriba abajo.
"""
import pathlib
import re
import threading

import pytest

pytestmark = pytest.mark.journey


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


def _nvs_partition(repo: pathlib.Path) -> tuple:
    """(offset, tamaño) de la partición nvs, de partitions.csv (FSD §2.2)."""
    for line in (repo / "partitions.csv").read_text().splitlines():
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
    if any(pattern in ln for ln in lines):
        return lines
    seen = {}
    mon = threading.Thread(target=lambda: seen.update(tb.serial_monitor(slot, pattern=pattern, timeout=15)))
    mon.start()
    import time; time.sleep(1)  # el monitor tiene que estar esperando antes del reset
    second = tb.serial_reset(slot)
    mon.join(25)
    return lines + ["--- segundo reset ---"] + _lines(second) + ["--- monitor ---"] + _lines(seen)


def test_jrn_01_0_flash_ci_image(testbench, dut_slot, firmware, boot_marker,
                                 bench_image_marker, commit_under_test, run_dir, tmp_path):
    """JRN-01.0 · C-HW-02 — la imagen de banco de la CI arranca en SLOT1 con la NVS borrada."""
    tb, tid, name = testbench, "JRN-01.0", "Grabar la imagen de la CI"
    repo = pathlib.Path(__file__).resolve().parents[2]
    tb.test_start("JRN-01 villa-nodo-clima-piloto", "Fase 1", total=1)
    evidence = [f"# {tid} — {name}", "", f"- commit bajo prueba: `{commit_under_test}`",
                f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})",
                f"- slot: {dut_slot}", ""]
    result, detail = "FAIL", ""
    try:
        # --- Precondiciones
        tb.test_step(tid, name, "Precondiciones: slot presente y libre")
        slot = tb.get_slot(dut_slot)
        if not slot.get("present"):
            pytest.skip(f"not done: {dut_slot} no presente (state {slot.get('state')})")
        assert firmware["variant"] == "bench", \
            f"JRN-01.0 graba la imagen de banco; llegó la variante {firmware['variant']}"

        # --- Ejecución: flasheo con los offsets de flash_args + NVS borrada (P-NVS-ERASE)
        images = _parse_flash_args(firmware["dir"] / "coldflash")
        nvs_off, nvs_size = _nvs_partition(repo)
        assert nvs_off not in images, "flash_args ya escribe en la NVS"
        blank = tmp_path / "nvs_blank.bin"
        blank.write_bytes(b"\xff" * nvs_size)
        images[nvs_off] = str(blank)
        evidence += ["## Flasheo", ""] + [f"- `{o}` {pathlib.Path(p).name}" for o, p in sorted(images.items(), key=lambda kv: int(kv[0], 16))] + [""]
        tb.test_step(tid, name, f"Grabando {len(images)} imágenes en {dut_slot} (NVS en blanco)")
        res = tb.flash(dut_slot, images, chip="esp32s3")
        evidence += [f"- respuesta: ok={res.get('ok')} returncode={res.get('returncode')}", ""]
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"

        # --- Ejecución: captura del arranque (P-BOOT-CAPTURE)
        tb.test_step(tid, name, f"Reset y captura del arranque: {bench_image_marker}, {boot_marker}")
        lines = _boot_capture(tb, dut_slot, boot_marker)
        (run_dir / f"{tid}-boot.log").write_text("\n".join(lines) + "\n")
        evidence += ["## Arranque", "", f"- log: `{tid}-boot.log` ({len(lines)} líneas)", ""]

        # --- Resultado
        boot = _after_last_reset(lines)
        assert boot, "la captura no contiene ninguna línea rst: (el reset no se vio)"
        has_marker = any(bench_image_marker in ln for ln in boot)
        has_init = any(boot_marker in ln for ln in boot)
        ver = next((ln for ln in boot if re.search(r"nodo_clima \S+", ln)), "")
        evidence += [f"- tras el último `rst:` ({len(boot)} líneas):",
                     f"- `{bench_image_marker}`: {'sí' if has_marker else 'NO'}",
                     f"- `{boot_marker}`: {'sí' if has_init else 'NO'}",
                     f"- versión en el log: `{ver.strip()}`", ""]
        assert has_marker, f"{bench_image_marker} no aparece en el arranque"
        assert has_init, f"«{boot_marker}» no aparece en el arranque"
        assert firmware["version"] in ver, f"el log no muestra la versión {firmware['version']}"
        result, detail = "PASS", f"{firmware['version']} arranca: {bench_image_marker} + {boot_marker}"
    except pytest.skip.Exception as e:
        result, detail = "SKIP", str(e)
        raise
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
        raise
    finally:
        tb.test_result(tid, name, result, detail[:200])
        tb.test_end()
        evidence += [f"**Resultado: {result}** — {detail}", ""]
        (run_dir / f"{tid}.md").write_text("\n".join(evidence))
