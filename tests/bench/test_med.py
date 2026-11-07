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


MED01_MENSAJES = 11            # FR-MED-01: 11 mensajes consecutivos → 10 intervalos
MED01_RANGO = (59.0, 61.0)


def _serie_med01(msgs, base, tema, t0):
    """Temperaturas en vivo de la última sesión MQTT (CR-TB-12: el reset del banco puede dar dos
    arranques), sin la de T11, que repite la última lectura (FR-MQTT-06) y no es un ciclo.
    La sesión empieza en su status de T11 (uptime_s < 60); la medida de T11 llega pegada a él."""
    inicio = None
    for m in msgs:
        if m["topic"] == f"{base}/status" and not m["retain"] and m["payload"] and m["t"] >= t0:
            try:
                st = json.loads(m["payload"])
            except json.JSONDecodeError:
                continue
            if st.get("estado") == "online" and isinstance(st.get("uptime_s"), int) and st["uptime_s"] < 60:
                inicio = m["t"]
    if inicio is None:
        return []
    return [m for m in msgs if m["topic"] == tema and not m["retain"] and m["payload"]
            and m["t"] > inicio + 1.5][:MED01_MENSAJES]


def test_tc_med_01_period_60_s(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-MED-01 · FR-MED-01 — OPERATIVO, sin salida a Internet: 11 mensajes consecutivos de
    temperatura recibidos en vivo; los 10 intervalos entre llegadas en [59, 61] s, sin dos
    publicaciones en el mismo ciclo. Fuera de JRN-01.6, que necesita bench-ap-internet (H-64)."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    tema = f"{base}/temperatura"
    with case(tb, "TC-MED-01", "Periodo de medición de 60 s", run_dir,
              spec="TC-MED villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            c.step(f"Capturar {MED01_MENSAJES} mensajes de temperatura en vivo")
            fin = time.time() + 60 * (MED01_MENSAJES + 2)
            while time.time() < fin and len(_serie_med01(sub.mensajes(), base, tema, t0)) < MED01_MENSAJES:
                time.sleep(2)
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])
        vivos = [m for m in msgs if m["topic"] == tema and not m["retain"] and m["payload"] and m["t"] >= t0]
        serie = _serie_med01(msgs, base, tema, t0)
        intervalos = [round(b["t"] - a["t"], 2) for a, b in zip(serie, serie[1:])]
        c.note("", "## Resultado", "",
               f"- mensajes de temperatura en vivo: {len(vivos)}; de la última sesión, sin el de T11: {len(serie)}",
               f"- intervalos (s): {intervalos}",
               f"- deriva acumulada en {len(intervalos)} ciclos: "
               f"{(serie[-1]['t'] - serie[0]['t']) - 60 * len(intervalos):+.2f} s" if len(serie) > 1 else "- sin serie")
        assert len(serie) == MED01_MENSAJES, f"solo {len(serie)} mensajes consecutivos (se esperaban {MED01_MENSAJES})"
        fuera = [x for x in intervalos if not MED01_RANGO[0] <= x <= MED01_RANGO[1]]
        assert not fuera, f"intervalos fuera de [59, 61] s: {fuera}"
        deriva = (serie[-1]["t"] - serie[0]["t"]) - 60 * len(intervalos)
        assert abs(deriva) <= 2, f"deriva acumulada {deriva:+.2f} s > 2 s"
        c.passed(f"10 intervalos en [{min(intervalos)}, {max(intervalos)}] s; deriva {deriva:+.2f} s")
