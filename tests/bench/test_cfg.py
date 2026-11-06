"""TC-CFG-* — configuración persistente (FSD §17), nivel bench. TC-CFG-02 necesita
al operador: el banco no corta la alimentación (bench-power-cycle en no); el
corte se pide con un aviso bloqueante en la UI del banco (bench-operator-prompt)."""
import re
import time

import pytest

from benchlib import _parse_flash_args, aprovisionar, case, esperar_lineas, primera

CORTES = 5                      # contrato de FR-CFG-01 (fila de cortes de alimentación)
ESPERA_AVISO_S = 600            # lo que el aviso espera a que el operador pulse «Hecho»
AVISO = ("Corte de alimentación {n} de {total} (TC-CFG-02): desenchufa los DOS cables USB-C de la "
         "placa del SLOT1, espera 5 segundos, vuelve a enchufarlos y pulsa «Hecho».")


def test_tc_cfg_02_power_cuts(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CFG-02 · FR-CFG-01 (fila de cortes) — 5 cortes de alimentación: cada arranque
    muestra cfg: con el mismo sitio y zona y con: ARRANQUE -> CONECTANDO_WIFI; nunca el portal."""
    tb = testbench
    ssid_portal = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "TC-CFG-02", "Cinco cortes de alimentación", run_dir, spec="TC-CFG villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot}")
        res = tb.flash(dut_slot, _parse_flash_args(firmware["dir"] / "coldflash"), chip="esp32s3")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"
        aprovisionar(tb, dut_slot, ssid_portal, c, tmp_path)
        time.sleep(8)    # el reinicio de T05 llega a los 4 s
        resultados = []
        for n in range(1, CORTES + 1):
            c.step(f"Corte {n}/{CORTES}: aviso al operador")
            t_aviso = time.time()
            if not tb.human_interaction(AVISO.format(n=n, total=CORTES), timeout=ESPERA_AVISO_S):
                pytest.skip(f"not done: el operador no confirmó el corte {n} (cancelado o {ESPERA_AVISO_S} s)")
            vistas = esperar_lineas(tb, dut_slot, t_aviso, ["con: ARRANQUE -> "], timeout=40)
            boots = [e for e in vistas if "boot: " in e.get("text", "") and " fw=" in e.get("text", "")]
            if not boots:
                pytest.skip(f"not done: la consola no capturó el arranque tras el corte {n} (instrumento, no el DUT)")
            ult = vistas.index(boots[-1])
            tras = vistas[ult:]
            boot = boots[-1]["text"].strip()
            cfg = primera(tras, "cfg: ")
            con = primera(tras, "con: ARRANQUE -> ")
            resultados.append((n, boot, cfg["text"].strip() if cfg else None, con["text"].strip() if con else None))
            c.save_log(f"corte{n}", [c._r(e["text"]) for e in vistas])
        c.note("", "## Resultado", "", *[f"- corte {n}: `{re.sub(r'^.*boot: ', 'boot: ', b)}` · "
                                         f"`{(g or 'sin cfg:').split('nodo: ')[-1]}` · `{(k or 'sin con:').split('nodo: ')[-1]}`"
                                         for n, b, g, k in resultados])
        for n, b, g, k in resultados:
            # Control positivo: fue un corte de verdad (encendido), no un reset del banco
            assert "reset=poweron" in b, f"corte {n}: el arranque no es un encendido ({b})"
            assert firmware["version"] in b, f"corte {n}: no es la imagen {firmware['version']}"
            assert g and "cfg: sitio=sitio1 zona=zona1" in g, f"corte {n}: falta cfg: sitio=sitio1 zona=zona1 ({g})"
            assert k and "con: ARRANQUE -> CONECTANDO_WIFI (fin_arranque)" in k, f"corte {n}: abrió el portal o no hizo T01 ({k})"
        c.passed(f"{CORTES} encendidos con cfg: sitio=sitio1 zona=zona1 y T01; ningún portal")
