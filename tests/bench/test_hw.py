"""TC-HW-* — restricciones de hardware (FSD §2.2), nivel target observado por el banco.
Atómicos: cada uno graba lo que necesita y deja el DUT con la imagen de la CI del
commit bajo prueba."""
import os
import pathlib
import re
import subprocess
import time

import pytest

from benchlib import _after_last_reset, _boot_capture, _lines, _parse_flash_args, case, esperar_lineas

REPO = pathlib.Path(__file__).resolve().parents[2]
USB_C_HW_01 = {"303a:1001", "1a86:55d3"}     # USB-Serial/JTAG nativo y CH343 (un solo USB-C con hub)


def _grabar(tb, slot, firmware):
    res = tb.flash(slot, _parse_flash_args(firmware["dir"] / "coldflash"), chip="esp32s3")
    assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"


def test_tc_hw_02_chip_reading(testbench, dut_slot, run_dir):
    """TC-HW-02 · C-HW-01, C-HW-02 (target) — esptool sobre la placa: ESP32-S3 con PSRAM de 8 MB,
    flash de 8 MB y las dos interfaces USB del único conector."""
    tb = testbench
    with case(tb, "TC-HW-02", "Lectura del chip y de la flash", run_dir, spec="TC-HW villa-nodo-clima-piloto") as c:
        c.step(f"Precondiciones: {dut_slot} presente")
        slot = tb.get_slot(dut_slot)
        if not slot.get("present"):
            pytest.skip(f"not done: {dut_slot} no presente")
        usb = {d.get("vid_pid") for d in slot.get("usb_devices") or []}
        c.step("POST /api/chip/info (esptool en el Pi; la placa se reinicia sola)")
        r = tb._api_post("/api/chip/info", {"slot": dut_slot}, timeout=60)
        c.save_log("esptool", (r.get("output") or "").splitlines())
        c.note("", "## Resultado", "", f"- chip: `{r.get('chip')}` {r.get('revision')}", f"- features: `{r.get('features')}`",
               f"- flash: `{r.get('flash_size')}`", f"- USB del slot: {sorted(usb)}")
        assert r.get("ok") and r.get("returncode", 0) == 0, f"chip/info falló: {r.get('error') or r.get('returncode')}"
        assert str(r.get("chip", "")).startswith("ESP32-S3"), f"chip {r.get('chip')} (C-HW-01)"
        assert "Embedded PSRAM 8MB" in str(r.get("features", "")), "el módulo no es N8R8: sin PSRAM de 8 MB (C-HW-01)"
        assert r.get("flash_size") == "8MB", f"flash de {r.get('flash_size')}, se esperan 8 MB (C-HW-01/02)"
        assert USB_C_HW_01 <= usb, f"interfaces USB {sorted(usb)}: faltan {sorted(USB_C_HW_01 - usb)} (C-HW-01)"
        c.passed("ESP32-S3 con PSRAM de 8 MB, flash de 8 MB y las dos interfaces del único USB-C")


def test_tc_hw_03_boots_without_psram(testbench, dut_slot, firmware, run_dir):
    """TC-HW-03 · C-HW-03 (target) — la imagen de la CI, construida con la PSRAM deshabilitada
    (lo comprueba build_checks.py en la CI), llega a fin_arranque en ≤ 120 s sin abortar ni reiniciarse."""
    tb = testbench
    with case(tb, "TC-HW-03", "Arranque sin PSRAM", run_dir, spec="TC-HW villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot}")
        _grabar(tb, dut_slot, firmware)
        c.step("Reset y 120 s de observación")
        t0 = time.time()
        reset = _lines(tb.serial_reset(dut_slot))
        time.sleep(max(0.0, t0 + 120 - time.time()))
        buf = [e.get("text", "") for e in esperar_lineas(tb, dut_slot, t0, [], timeout=0)]
        lineas = _after_last_reset(reset) + ["--- buffer del slot ---"] + buf
        c.save_log("serie", lineas)
        boot = _after_last_reset(reset) or buf
        fin = next((l for l in boot + buf if re.search(r"con: ARRANQUE -> (CONECTANDO_WIFI|PORTAL) \(fin_arranque\)", l)), None)
        e1 = sorted({l.strip() for l in boot + buf if "boot: " in l and " fw=" in l})
        malos = [l for l in boot + buf if "Guru Meditation" in l or "abort()" in l]
        c.note("", "## Resultado", "", f"- fin_arranque: `{(fin or 'no').strip()}`", f"- líneas E1: {len(e1)}",
               f"- Guru Meditation / abort(): {len(malos)}")
        assert any(firmware["version"] in l for l in e1), f"el arranque no es la imagen {firmware['version']}"
        assert fin, "sin con: ARRANQUE -> … (fin_arranque) en 120 s"
        assert not malos, f"el log muestra {malos[0][:80]}"
        assert len(e1) == 1, f"{len(e1)} arranques en la ventana: el nodo se reinició"
        c.passed("fin_arranque sin PSRAM, sin abortar y con un solo arranque en 120 s")


def test_tc_hw_05_i2c_scan(testbench, dut_slot, firmware, run_dir, tmp_path):
    """TC-HW-05 · C-HW-04, C-HW-05 (target) — la sonda tests/target/i2c_probe escanea el bus en
    GPIO8/9 a 100 kHz con solo los pull-ups externos: ack con 0x44. Después se restaura la imagen."""
    tb = testbench
    with case(tb, "TC-HW-05", "Escaneo del bus I²C del SHT41", run_dir, spec="TC-HW villa-nodo-clima-piloto") as c:
        bdir = tmp_path / "probe"
        c.step("Precondiciones: construir la sonda tests/target/i2c_probe con ESP-IDF")
        b = subprocess.run(["bash", "-c", f'. "$IDF_PATH/export.sh" >/dev/null 2>&1 && idf.py -C {REPO}/tests/target/i2c_probe '
                            f'-B {bdir} -DSDKCONFIG={bdir}/sdkconfig set-target esp32s3 build'],
                           capture_output=True, text=True, env=dict(os.environ))
        if b.returncode != 0:
            pytest.skip(f"not done: la sonda no se construye (rc {b.returncode}): {b.stdout[-300:]}")
        imgs = {}
        for l in (bdir / "flash_args").read_text().splitlines():
            p = l.split()
            if len(p) == 2 and p[0].startswith("0x"):
                imgs[p[0]] = str(bdir / p[1])
        try:
            c.step(f"Grabar la sonda en {dut_slot} y capturar su arranque")
            res = tb.flash(dut_slot, imgs, chip="esp32s3")
            assert res.get("ok") and res.get("returncode", 0) == 0, f"flash de la sonda falló: {res.get('error') or res}"
            lineas = _after_last_reset(_boot_capture(tb, dut_slot, "probe: Init complete"))
            c.save_log("sonda", lineas)
        finally:
            c.step("Restaurar la imagen de la CI del commit bajo prueba")
            _grabar(tb, dut_slot, firmware)
        hasta = next((i for i, l in enumerate(lineas) if "probe: Init complete" in l), None)
        escaneos = [l.strip() for l in (lineas[:hasta] if hasta is not None else lineas) if "i2c: scan sda=8 scl=9 hz=100000" in l]
        contado = escaneos[-1] if escaneos else None     # el último: solo pull-ups externos (E12)
        c.note("", "## Resultado", "", *[f"- `{re.sub(r'^.*i2c: ', 'i2c: ', l)}`" for l in escaneos],
               f"- el que cuenta (pull-ups externos): `{contado}`")
        assert hasta is not None, "la sonda no llegó a «Init complete»"
        assert contado, "sin línea «i2c: scan sda=8 scl=9 hz=100000 …» (E12)"
        acks = re.search(r"ack=(\S+)", contado).group(1)
        assert acks != "ninguno" and "0x44" in acks.split(","), f"ack={acks}: el SHT41 no responde en 0x44 (C-HW-04/05)"
        c.passed(f"escaneo con pull-ups externos: ack={acks}")
