"""TC-CFG-* — configuración persistente (FSD §17), nivel bench. TC-CFG-02 necesita
al operador: el banco no corta la alimentación (bench-power-cycle en no); cada corte se
pide con avisos en la UI del banco (bench-operator-prompt) y se observa por MQTT, porque
la consola del banco no captura el arranque tras un corte (CR-TB-10, FSD 0.9.6)."""
import pytest

from benchlib import case, suscriptor_mqtt
from cortes import corte, errores, filtros, guardar_mqtt, limpiar, preparar, resumen, sin_hacer

CORTES = 5                      # contrato de FR-CFG-01 (fila de cortes de alimentación)


def test_tc_cfg_02_power_cuts(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CFG-02 · FR-CFG-01 (fila de cortes) — 5 cortes de alimentación con el suscriptor
    conectado desde antes: tras cada uno, el primer status en vivo (retain = 0) llega con
    reset = poweron bajo sitio1/zona1/<nodo>/status; nunca el portal (escaneo sin clima-*)."""
    from test_mqtt import configurado
    tb = testbench
    nodo = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "TC-CFG-02", "Cinco cortes de alimentación", run_dir, spec="TC-CFG villa-nodo-clima-piloto") as c:
        resultados = []
        with configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
            c.step("Arrancar el broker y suscribirse antes del primer corte (cualquier sitio/zona del nodo)")
            banco.broker_on()
            with suscriptor_mqtt(tb, filtros(nodo), limpiar=limpiar(nodo)) as sub:
                t0, reg = preparar(tb, dut_slot, banco, sub, c)
                try:
                    for n in range(1, CORTES + 1):
                        resultados.append(corte(tb, dut_slot, sub, nodo, "TC-CFG-02", n, CORTES, c, banco))
                finally:
                    guardar_mqtt(c, sub, t0)
                    c.save_log("serie", [e["text"] for e in reg.leer()])
                    c.note("", "## Resultado", "", *[resumen(r) for r in resultados])
        mal = [e for r in resultados for e in errores(r, nodo, arranque=False)]
        assert not mal, "; ".join(mal)
        falta = [e for r in resultados for e in sin_hacer(r)]
        if falta:
            pytest.skip("not done: " + "; ".join(falta))
        c.passed(f"{CORTES} encendidos con status reset=poweron bajo sitio1/zona1/{nodo}/status; ningún portal")
