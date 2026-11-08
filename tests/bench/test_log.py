"""TC-LOG-03 — FR-LOG-03: el log UDP nunca bloquea a quien escribe (FSD §18.1; Fase 2).
Necesita la variante de imagen de banco con el log UDP hacia una IP sin uso de la red del
AP del banco (H-67): pytest … --ci-variant bench-sin-receptor. Atómico: graba esa imagen,
aprovisiona contra un AP desechable nuevo y deja el AP y el broker apagados al terminar."""
import json
import time

import pytest

from benchlib import case
from test_mqtt import MEDIDAS, _a_operativo, _nodo, _suscribir, configurado

CICLOS = 10
RANGO = (59.0, 61.0)


def test_tc_log_03_udp_log_to_nowhere(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-LOG-03 · FR-LOG-03 — imagen con CONFIG_NODO_UDP_LOG_HOST en una IP sin uso, 10 ciclos:
    en cada uno, las 3 medidas en vivo y un status; intervalos entre temperaturas en [59, 61] s;
    uptime_s siempre creciente (sin reinicio ni bloqueo)."""
    tb = testbench
    if firmware["variant"] != "bench-sin-receptor":
        pytest.skip("not done: TC-LOG-03 necesita --ci-variant bench-sin-receptor (H-67)")
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-LOG-03", "Log UDP hacia una IP sin receptor", run_dir,
              spec="TC-LOG villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.note("- variante bench-sin-receptor: log UDP hacia una IP sin uso de la red del AP del banco", "")
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            c.step(f"Observar {CICLOS} ciclos de medición")
            fin = time.time() + 60 * (CICLOS + 3)
            while time.time() < fin:
                st = [m for m in sub.mensajes() if m["topic"] == f"{base}/status" and not m["retain"] and m["t"] >= t0]
                if len(st) >= CICLOS + 2:
                    break
                time.sleep(2)
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])
        vivos = [m for m in msgs if m["t"] >= t0 and not m["retain"] and m["payload"]]
        status = []
        for m in vivos:
            if m["topic"] == f"{base}/status":
                s = json.loads(m["payload"])
                if s.get("estado") == "online":
                    status.append((m["t"], s))
        # Ciclos: cada status de ciclo llega justo después de sus medidas; el primero es el de T11
        ciclos = status[1:CICLOS + 1]
        faltan = []
        for t_st, s in ciclos:
            medidas = {m["topic"].rsplit("/", 1)[-1] for m in vivos if m["topic"].rsplit("/", 1)[-1] in MEDIDAS
                       and t_st - 5 <= m["t"] <= t_st}
            if len(medidas) != 3:
                faltan.append((round(t_st - t0), sorted(medidas)))
        temps = [m["t"] for m in vivos if m["topic"] == f"{base}/temperatura" and ciclos and
                 ciclos[0][0] - 5 <= m["t"] <= ciclos[-1][0]]
        intervalos = [round(b - a, 2) for a, b in zip(temps, temps[1:])]
        ups = [s["uptime_s"] for _, s in status]
        c.note("", "## Resultado", "",
               f"- status en vivo: {len(status)}; ciclos observados: {len(ciclos)}",
               f"- ciclos sin las 3 medidas: {faltan or 'ninguno'}",
               f"- intervalos entre temperaturas (s): {intervalos}",
               f"- uptime_s: {ups}")
        assert len(ciclos) == CICLOS, f"solo {len(ciclos)} ciclos con status (se esperaban {CICLOS})"
        assert not faltan, f"ciclos sin las 3 medidas: {faltan}"
        fuera = [x for x in intervalos if not RANGO[0] <= x <= RANGO[1]]
        assert len(intervalos) == CICLOS - 1 and not fuera, f"intervalos fuera de [59, 61] s o incompletos: {intervalos}"
        assert all(b > a for a, b in zip(ups, ups[1:])), f"uptime_s no creciente (reinicio): {ups}"
        c.passed(f"{CICLOS} ciclos con 3 medidas y status; intervalos en [{min(intervalos)}, {max(intervalos)}] s; sin reinicio")
