"""TC-MED-* de banco — ciclo de medición observado por MQTT (FSD §5, §9.3; Fase 2).
Atómicos: graban la imagen de la CI, aprovisionan contra un AP desechable nuevo y dejan el
AP y el broker apagados al terminar."""
import json
import time

from benchlib import case
from test_mqtt import MEDIDAS, _a_operativo, _nodo, _suscribir, configurado

BROKER_PARADO_S = 600          # FR-MED-02: broker detenido 10 min
VUELTA_S = 150                 # del broker de vuelta al primer status (backoff ≤ 60 s + ciclo)


def _status(msgs, base, desde=0.0, hasta=float("inf")):
    out = []
    for m in msgs:
        if m["topic"] == f"{base}/status" and not m["retain"] and m["payload"] and desde <= m["t"] <= hasta:
            try:
                st = json.loads(m["payload"])
            except json.JSONDecodeError:
                continue
            if st.get("estado") == "online":
                out.append((m, st))
    return out


def test_tc_med_02_cycle_without_broker(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-MED-02 · FR-MED-02 — broker detenido 10 min: entre el último status previo al corte y
    el primero posterior, Δlecturas = ⌊Δuptime_s / 60⌋ ± 1, sin reinicio (uptime creciente)."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-MED-02", "Medición con el broker parado 10 min", run_dir,
              spec="TC-MED villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            c.step("Esperar dos status en vivo (al conectar y en el ciclo siguiente)")
            fin = time.time() + 150
            while time.time() < fin and len(_status(sub.mensajes(), base, t0)) < 2:
                time.sleep(1)
            time.sleep(2)
            c.step(f"Parar el broker {BROKER_PARADO_S // 60} min")
            t_off = time.time()
            banco.broker_off()
            time.sleep(BROKER_PARADO_S)
            c.step("Arrancar el broker; esperar el primer status en vivo")
            t_on = time.time()
            banco.broker_on()
            fin = t_on + VUELTA_S
            while time.time() < fin and not _status(sub.mensajes(), base, t_on):
                time.sleep(1)
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])
        antes = _status(msgs, base, t0, t_off)
        despues = _status(msgs, base, t_on)
        assert len(antes) >= 2, f"precondición: {len(antes)} status en vivo antes del corte (se esperaban 2)"
        assert despues, f"ningún status en vivo en {VUELTA_S} s tras arrancar el broker"
        a, d = antes[-1][1], despues[0][1]
        du, dl = d["uptime_s"] - a["uptime_s"], d["lecturas"] - a["lecturas"]
        esperado = du // 60
        c.note("", "## Resultado", "",
               f"- último status antes del corte: uptime_s={a['uptime_s']}, lecturas={a['lecturas']}, reset={a['reset']}",
               f"- primer status tras el broker: a {despues[0][0]['t'] - t_on:+.1f} s, uptime_s={d['uptime_s']}, "
               f"lecturas={d['lecturas']}, reset={d['reset']}",
               f"- Δuptime_s={du} → ⌊Δ/60⌋={esperado}; Δlecturas={dl} (tolerancia ± 1)")
        assert du > BROKER_PARADO_S, f"Δuptime_s={du} ≤ {BROKER_PARADO_S}: el nodo se reinició"
        assert dl != 0, "lecturas sin cambio: el ciclo se paró sin broker"
        assert abs(dl - esperado) <= 1, f"Δlecturas={dl}, esperado {esperado} ± 1"
        c.passed(f"Δlecturas={dl} con Δuptime_s={du} (⌊Δ/60⌋={esperado}); sin reinicio")
