"""TC-SEN-* — driver SHT41 (FSD §8), nivel target observado por el banco.
Atómico: graba la imagen de la CI del commit bajo prueba (sin tocar la NVS: el
ciclo corre en cualquier estado, FR-MED-02) y observa su log serie."""
import re
import time

from benchlib import _after_last_reset, _lines, _parse_flash_args, case

CICLOS = 3
CICLO_S = 60
MED = re.compile(r"med: T=(-?\d+\.\d) HR=(\d+\.\d) Td=(-?\d+\.\d|-)")


def test_tc_sen_03_three_cycles(testbench, dut_slot, firmware, run_dir):
    """TC-SEN-03 · FR-SEN-01 (target) — 3 ciclos con el sensor conectado: 3 líneas med: con T ∈ [0, 50] °C."""
    tb = testbench
    with case(tb, "TC-SEN-03", "Tres ciclos de medición con el SHT41", run_dir,
              spec="TC-SEN villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot} (NVS intacta)")
        images = _parse_flash_args(firmware["dir"] / "coldflash")
        res = tb.flash(dut_slot, images, chip="esp32s3")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"

        c.step(f"Reset y observación de {CICLOS} ciclos ({CICLOS} × {CICLO_S} s)")
        t0 = time.time()
        reset_out = tb.serial_reset(dut_slot)
        fin = t0 + (CICLOS - 1) * CICLO_S + 30
        vistas = []
        while time.time() < fin:
            out = tb.serial_output(dut_slot, lines=500, since=t0)
            vistas = [e if isinstance(e, dict) else {"text": str(e), "ts": 0} for e in (out.get("lines") or [])]
            if sum("med: " in e.get("text", "") for e in vistas) >= CICLOS:
                break
            time.sleep(2)
        lines = _lines(reset_out) + ["--- buffer del slot ---"] + [e.get("text", "") for e in vistas]
        c.save_log("serie", lines)

        boot = _after_last_reset(_lines(reset_out))
        fw = next((ln for ln in boot + lines if "boot: " in ln and " fw=" in ln), "")
        meds = [e for e in vistas if "med: " in e.get("text", "")]
        c.note("", "## Resultado", "", f"- arranque: `{fw.strip()}`",
               *[f"- ts {e.get('ts', 0) - t0:+.1f} s: `{e['text'].strip()}`" for e in meds])
        if len(meds) >= 2:
            dts = [round(b.get("ts", 0) - a.get("ts", 0), 1) for a, b in zip(meds, meds[1:])]
            c.note(f"- intervalos entre líneas med: {dts} s (informativo; FR-MED-01 es de la Fase 2)")
        assert firmware["version"] in fw, f"el arranque no es la imagen {firmware['version']}: «{fw.strip()}»"
        invalidas = [e["text"] for e in meds if "med: invalida" in e["text"]]
        assert not invalidas, f"lecturas inválidas: {invalidas}"
        assert len(meds) >= CICLOS, f"{len(meds)} líneas med: en {fin - t0:.0f} s; se esperaban {CICLOS}"
        for e in meds[:CICLOS]:
            m = MED.search(e["text"])
            assert m, f"línea med: sin el formato de E3: «{e['text'].strip()}»"
            t = float(m.group(1))
            assert 0.0 <= t <= 50.0, f"T = {t} °C fuera de [0, 50]"
        c.passed(f"{CICLOS} líneas med: válidas con T en [0, 50] °C")
