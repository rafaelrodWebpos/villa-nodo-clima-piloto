"""TC-TIME-* de banco — sin hora válida (FSD §13; Fase 2). El AP del banco no tiene salida a
Internet (bench-ap-internet en no, CR-TB-01): SNTP es inalcanzable desde el arranque, que es
la precondición de FR-TIME-05 y FR-TIME-06. Atómicos: graban la imagen de la CI, aprovisionan
contra un AP desechable nuevo y dejan el AP y el broker apagados al terminar."""
import json
import re
import time

from benchlib import case
from test_mqtt import MEDIDAS, _a_operativo, _ms, _nodo, _suscribir, configurado, _ultimo_arranque

MEDIDA_LIMITE_S = 30            # FR-TIME-05, desde el encendido estimado como en FR-CON-05
CON_IP_S = 300                  # FR-TIME-06: DUT con IP durante 5 min
SNTP_MAX_S = 15                 # FR-TIME-06
WIFI_UP = "con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)"


def test_tc_time_05_publish_without_time(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-TIME-05 · FR-TIME-05 — SNTP inalcanzable desde el arranque: la primera medida en vivo
    llega ≤ 30 s después del encendido estimado (llegada del primer status − uptime_s − 2 s),
    con "ts": null, y el status dice hora_valida = false."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-TIME-05", "Medir y publicar sin hora", run_dir, spec="TC-TIME villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.note("- AP del banco sin salida a Internet: SNTP inalcanzable desde el arranque", "")
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            fin = time.time() + 90
            while time.time() < fin and not any(m["topic"].rsplit("/", 1)[-1] in MEDIDAS and not m["retain"]
                                                and m["t"] >= t0 for m in sub.mensajes()):
                time.sleep(1)
            time.sleep(3)
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])
        vivos = [m for m in msgs if m["t"] >= t0 and not m["retain"] and m["payload"]]
        # La sesión que cuenta es la del último arranque (CR-TB-12: el reset del banco puede dar dos)
        st = [m for m in vivos if m["topic"] == f"{base}/status" and '"online"' in m["payload"]]
        assert st, "ningún status en vivo tras el reset"
        primero = st[-1]
        cuerpo = json.loads(primero["payload"])
        encendido = primero["t"] - cuerpo["uptime_s"] - 2
        med = next((m for m in vivos if m["topic"].rsplit("/", 1)[-1] in MEDIDAS and m["t"] >= primero["t"]), None)
        c.note("", "## Resultado", "",
               f"- primer status de la última sesión: uptime_s={cuerpo['uptime_s']}, hora_valida={cuerpo.get('hora_valida')}",
               f"- primera medida: " + (f"`{med['topic'].replace(base, '<base>')}` {med['payload']} a "
                                        f"{med['t'] - encendido:.1f} s del encendido estimado" if med else "ninguna"))
        assert med, "ninguna medida en vivo tras el status"
        assert med["t"] - encendido <= MEDIDA_LIMITE_S, f"primera medida a {med['t'] - encendido:.1f} s (> {MEDIDA_LIMITE_S} s)"
        cm = json.loads(med["payload"])
        assert "ts" in cm and cm["ts"] is None, f"la medida no lleva \"ts\": null: {med['payload']}"
        assert cuerpo.get("hora_valida") is False, f"hora_valida={cuerpo.get('hora_valida')} sin SNTP"
        c.passed(f"primera medida a {med['t'] - encendido:.1f} s del encendido estimado con ts=null; hora_valida=false")


def test_tc_time_06_sntp_retry_without_time(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-TIME-06 · FR-TIME-06 — SNTP inalcanzable; DUT con IP durante 5 min: los intervalos
    entre líneas «sntp: inicio <srv>» consecutivas (marcas del DUT) son ≤ 15 s, también después
    de un «sntp: fallo»."""
    tb = testbench
    nodo = _nodo(dut_mac)
    with case(tb, "TC-TIME-06", "Reintento SNTP sin hora", run_dir, spec="TC-TIME villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.note("- AP del banco sin salida a Internet: SNTP inalcanzable", "")
        banco.broker_on()
        with _suscribir(tb, nodo):
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            c.step(f"Observar la consola {CON_IP_S // 60} min con IP")
            time.sleep(CON_IP_S + 20)
        ent = _ultimo_arranque(reg)
        c.save_log("serie", [e["text"] for e in ent])
        textos = [e["text"].strip() for e in ent]
        up = next((t for t in textos if WIFI_UP in t), None)
        assert up, f"sin {WIFI_UP} en el último arranque"
        t_up = _ms(up)
        inicios = [(_ms(t), t) for t in textos if "sntp: inicio " in t and _ms(t) is not None and _ms(t) >= t_up]
        fallos = [t for t in textos if "sntp: fallo" in t]
        # Ventana con IP: de wifi_up a wifi_up + 5 min (marcas del DUT)
        ventana = [x for x in inicios if x[0] <= t_up + CON_IP_S * 1000]
        intervalos = [round((b[0] - a[0]) / 1000, 1) for a, b in zip(ventana, ventana[1:])]
        primero = (ventana[0][0] - t_up) / 1000 if ventana else None
        c.note("", "## Resultado", "",
               f"- primera «sntp: inicio» a {primero if primero is not None else '-'} s de wifi_up",
               f"- «sntp: inicio» en los 5 min: {len(ventana)}; intervalos (s): {intervalos}",
               f"- «sntp: fallo» en la captura: {len(fallos)}",
               f"- servidor: {ventana[0][1].split('sntp: inicio ')[-1] if ventana else '-'}")
        assert ventana, "ninguna «sntp: inicio» con IP"
        assert primero <= SNTP_MAX_S, f"la primera petición llegó a {primero} s de wifi_up"
        assert intervalos and max(intervalos) <= SNTP_MAX_S, f"intervalo > {SNTP_MAX_S} s: {intervalos}"
        assert len(ventana) >= CON_IP_S // SNTP_MAX_S, f"solo {len(ventana)} peticiones en {CON_IP_S} s"
        c.passed(f"{len(ventana)} peticiones en 5 min, intervalo máximo {max(intervalos)} s")
