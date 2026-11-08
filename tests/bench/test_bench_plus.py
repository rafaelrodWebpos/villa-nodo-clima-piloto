"""Nivel bench⁺: contratos que necesitan la salida a Internet del AP del banco (bench-ap-internet)
y el bloqueo de SNTP (bench-sntp-block), del fork villa-1 (H-73, H-75). Atómicos: graban la
imagen, aprovisionan contra un AP desechable nuevo y dejan el AP, el broker, la salida a
Internet y el bloqueo de SNTP apagados al terminar (ap_stop los apaga; además se fuerza).

El reloj del suscriptor es el de la laptop, sincronizado por NTP (se mide su desfase con
pool.ntp.org y va a la evidencia)."""
import json
import re
import socket
import struct
import time

import pytest

from benchlib import case
from test_banco_fork import _api, _estado, _sntp_block
from test_mqtt import MEDIDAS, _a_operativo, _ms, _nodo, _suscribir, configurado

WIFI_UP = "con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)"
SINC = re.compile(r"sntp: sincronizado ts=(\d+)")
SINC_LIMITE_S = 30          # FR-TIME-01
TS_TOL_S = 2                # FR-MQTT-03


def _desfase_ntp():
    """Reloj de la laptop menos pool.ntp.org, en s (None si no responde)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.sendto(b"\x1b" + 47 * b"\0", ("pool.ntp.org", 123))
        d, _ = s.recvfrom(48)
        t = struct.unpack("!12I", d)[10] + struct.unpack("!12I", d)[11] / 2**32 - 2208988800
        return round(time.time() - t, 2)
    except OSError:
        return None


def _apagar_fork():
    _api("POST", "/api/wifi/sntp_block", {"blocked": False})
    _api("POST", "/api/wifi/internet", {"enabled": False})


def _vivos(msgs, base, desde=0.0):
    out = []
    for m in msgs:
        if m["t"] >= desde and not m["retain"] and m["payload"] and m["topic"].startswith(base + "/"):
            try:
                out.append((m, json.loads(m["payload"])))
            except ValueError:
                pass
    return out


def _guardar(c, reg, msgs, t0):
    ent = reg.leer()
    c.save_log("serie", [e["text"] for e in ent])
    c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                        for m in msgs])
    return ent


def test_jrn_01_6_sntp_and_measures(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """JRN-01.6 · FR-MED-01, FR-MQTT-01, FR-MQTT-03, FR-TIME-01 — AP con salida a Internet desde
    que se levanta: «sntp: sincronizado» ≤ 30 s después de wifi_up (marcas del DUT) y hora_valida
    = true en el primer status posterior; llega en vivo una medida válida de cada tópico y la
    siguiente de temperatura 60 ± 1 s después; ts no nulo y |ts − llegada| ≤ 2 s. Pone su propia
    precondición (configurado), como JRN-01.7."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "JRN-01.6", "Hora por SNTP y medidas con ts", run_dir) as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        desfase = _desfase_ntp()
        c.note(f"- reloj del suscriptor (laptop) frente a pool.ntp.org: {desfase} s", "")
        banco.broker_on()
        try:
            with _suscribir(tb, nodo) as sub:
                t0, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
                st = _estado()
                c.step("Esperar dos ciclos de medida (≈ 130 s)")
                fin = time.time() + 140
                while time.time() < fin:
                    temps = [m for m, _ in _vivos(sub.mensajes(), base, t0) if m["topic"] == f"{base}/temperatura"]
                    if len(temps) >= 3:
                        break
                    time.sleep(2)
                time.sleep(3)
                msgs = sub.mensajes()
        finally:
            _apagar_fork()
        ent = _guardar(c, reg, msgs, t0)
        textos = [e["text"].strip() for e in ent]
        up = next((t for t in reversed(textos) if WIFI_UP in t), None)
        sinc = next((t for t in textos if SINC.search(t) and up and (_ms(t) or 0) >= (_ms(up) or 0)), None)
        dt_sinc = (_ms(sinc) - _ms(up)) / 1000 if up and sinc else None
        vivos = _vivos(msgs, base, t0)
        st_vivos = [(m, p) for m, p in vivos if m["topic"] == f"{base}/status" and p.get("estado") == "online"]
        st_tras = next(((m, p) for m, p in st_vivos if sinc and p.get("uptime_s", 0) * 1000 >= _ms(sinc)), None)
        por_tema = {k: [(m, p) for m, p in vivos if m["topic"] == f"{base}/{k}"] for k in MEDIDAS}
        con_ts = [(m, p) for m, p in vivos if m["topic"].rsplit("/", 1)[-1] in MEDIDAS and isinstance(p.get("ts"), int)]
        desv = [round(p["ts"] - m["t"], 2) for m, p in con_ts]
        temps = por_tema["temperatura"]
        # La de T11 repite la última lectura (FR-MQTT-06): el intervalo se mide entre las siguientes
        ciclo = [round(b[0]["t"] - a[0]["t"], 2) for a, b in zip(temps[1:], temps[2:])]
        c.note("", "## Resultado", "",
               f"- salida del AP: {st['internet']} (rules_ok {st['rules_ok']})",
               f"- wifi_up: `{up}`", f"- sincronización: `{sinc}` → {dt_sinc} s desde wifi_up (≤ {SINC_LIMITE_S} s)",
               "- primer status posterior: " + (f"uptime_s={st_tras[1]['uptime_s']}, hora_valida={st_tras[1].get('hora_valida')}" if st_tras else "ninguno"),
               *[f"- {k}: {len(v)} en vivo; primera `{v[0][0]['payload']}`" if v else f"- {k}: ninguna" for k, v in por_tema.items()],
               f"- intervalos entre medidas de temperatura (sin la de T11): {ciclo} s",
               f"- ts − llegada en las {len(con_ts)} medidas con ts: {desv}")
        assert up and sinc, "sin wifi_up o sin «sntp: sincronizado» en el último arranque"
        assert dt_sinc <= SINC_LIMITE_S, f"sincronizó a {dt_sinc} s de wifi_up"
        assert st_tras and st_tras[1].get("hora_valida") is True, f"primer status tras sincronizar: {st_tras}"
        assert all(v for v in por_tema.values()), f"falta algún tópico: {[k for k, v in por_tema.items() if not v]}"
        assert ciclo and all(59 <= x <= 61 for x in ciclo), f"intervalo de medida fuera de 60 ± 1 s: {ciclo}"
        tras = [(m, p) for m, p in vivos if m["topic"].rsplit("/", 1)[-1] in MEDIDAS and st_tras and m["t"] >= st_tras[0]["t"]]
        assert tras and all(isinstance(p.get("ts"), int) for _, p in tras), "medida sin ts tras la sincronización"
        assert all(abs(x) <= TS_TOL_S for x in desv), f"|ts − llegada| > {TS_TOL_S} s: {desv}"
        c.passed(f"sincroniza a {dt_sinc} s de wifi_up; hora_valida true; medidas con |ts − llegada| ≤ "
                 f"{max(abs(x) for x in desv):.2f} s; intervalo {ciclo} s")


def test_tc_med_06_reconnect_publishes_latest_only(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-MED-06 · FR-MED-06 (bench⁺) — OPERATIVO con hora válida; broker detenido 5 min y
    restablecido; suscriptor con los retenidos descartados: en la ventana [status online de la
    reconexión, +5 s] llega exactamente 1 mensaje por medida, con ts ≤ 60 s anterior a la
    llegada; ningún mensaje con ts de la ventana sin conexión (ni ráfaga)."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-MED-06", "Al reconectar, solo la lectura más reciente", run_dir,
              spec="TC-MED villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.note(f"- reloj del suscriptor (laptop) frente a pool.ntp.org: {_desfase_ntp()} s", "")
        banco.broker_on()
        try:
            with _suscribir(tb, nodo) as sub:
                t0, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
                c.step("Esperar hora válida (status con hora_valida = true)")
                fin = time.time() + 150
                while time.time() < fin and not any(p.get("hora_valida") for m, p in _vivos(sub.mensajes(), base, t0)
                                                    if m["topic"] == f"{base}/status"):
                    time.sleep(2)
                time.sleep(3)
                c.step("Parar el broker 5 min")
                t_off = time.time()
                banco.broker_off()
                time.sleep(300)
                c.step("Arrancar el broker; esperar el status online de la reconexión y 10 s más")
                t_on = time.time()
                banco.broker_on()
                fin = t_on + 150
                while time.time() < fin and not any(p.get("estado") == "online" for m, p in _vivos(sub.mensajes(), base, t_on)
                                                    if m["topic"] == f"{base}/status"):
                    time.sleep(1)
                time.sleep(10)
                msgs = sub.mensajes()
                conexiones = list(sub.conexiones)
        finally:
            _apagar_fork()
        _guardar(c, reg, msgs, t0)
        vivos = _vivos(msgs, base, t_on)
        st = next(((m, p) for m, p in vivos if m["topic"] == f"{base}/status" and p.get("estado") == "online"), None)
        assert st, "ningún status online tras arrancar el broker"
        t_st = st[0]["t"]
        sub_listo = max([t for t in conexiones if t <= t_st] or [0])
        ventana = [(m, p) for m, p in vivos if t_st <= m["t"] <= t_st + 5 and m["topic"].rsplit("/", 1)[-1] in MEDIDAS]
        cuenta = {k: sum(1 for m, _ in ventana if m["topic"] == f"{base}/{k}") for k in MEDIDAS}
        edades = {m["topic"].rsplit("/", 1)[-1]: (round(m["t"] - p["ts"], 1) if isinstance(p.get("ts"), int) else None)
                  for m, p in ventana}
        en_corte = [(m["topic"].rsplit("/", 1)[-1], p.get("ts")) for m, p in vivos
                    if m["topic"].rsplit("/", 1)[-1] in MEDIDAS and isinstance(p.get("ts"), int)
                    and t_off + 2 < p["ts"] < t_on - 62]
        c.note("", "## Resultado", "",
               f"- broker parado {t_on - t_off:.0f} s; suscriptor reconectado {t_st - sub_listo:.1f} s antes del status",
               f"- status de la reconexión a {t_st - t_on:+.1f} s de arrancar el broker: `{st[0]['payload']}`",
               f"- mensajes por medida en [status, +5 s]: {cuenta}",
               f"- edad (llegada − ts) de esos mensajes: {edades} s",
               f"- mensajes tras la reconexión con ts de la ventana sin conexión: {en_corte or 'ninguno'}")
        if not sub_listo:
            pytest.skip("not done: el suscriptor no estaba reconectado antes del status de la reconexión")
        assert all(n == 1 for n in cuenta.values()), f"no llega exactamente 1 por medida: {cuenta}"
        assert all(e is not None and -TS_TOL_S <= e <= 60 for e in edades.values()), f"ts fuera de [llegada − 60 s, llegada]: {edades}"
        assert not en_corte, f"mensajes con ts de la ventana sin conexión: {en_corte}"
        c.passed(f"1 mensaje por medida en la ventana; edades {edades} s; ninguna lectura del corte publicada")


BLOQUEO_S = 7200            # FR-TIME-04: SNTP bloqueado 2 h
LECTURA_CADA_S = 30


def test_tc_time_04_resync_failure_keeps_time(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-TIME-04 · FR-TIME-04 (bench⁺) — hora válida; SNTP bloqueado 2 h: hora_valida sigue en
    true en todos los status y todas las medidas llevan ts entero; el log registra «sntp: fallo»
    en el intento de resincronización (≈ 1 h después de la sincronización)."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-TIME-04", "Resincronización fallida sin perder la hora", run_dir,
              spec="TC-TIME villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        try:
            with _suscribir(tb, nodo) as sub:
                t0, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
                c.step("Esperar la sincronización")
                fin = time.time() + 90
                sinc = None
                while time.time() < fin and not sinc:
                    sinc = next((e for e in reg.leer() if SINC.search(e.get("text", ""))), None)
                    time.sleep(1)
                assert sinc, "no sincronizó con la salida encendida"
                time.sleep(65)              # un status con hora válida antes del bloqueo
                c.step(f"Bloquear SNTP {BLOQUEO_S // 3600} h")
                t_b = time.time()
                est_b = _sntp_block(True)
                while time.time() < t_b + BLOQUEO_S:
                    reg.leer()
                    time.sleep(min(LECTURA_CADA_S, max(1.0, t_b + BLOQUEO_S - time.time())))
                c.step("Desbloquear SNTP")
                est_u = _sntp_block(False)
                time.sleep(5)
                msgs = sub.mensajes()
        finally:
            _apagar_fork()
        ent = _guardar(c, reg, msgs, t0)
        vivos = _vivos(msgs, base, t_b)
        st = [p for m, p in vivos if m["topic"] == f"{base}/status" and p.get("estado") == "online"]
        meds = [(m, p) for m, p in vivos if m["topic"].rsplit("/", 1)[-1] in MEDIDAS]
        sin_ts = [m["payload"] for m, p in meds if not isinstance(p.get("ts"), int)]
        falsas = [p.get("hora_valida") for p in st if p.get("hora_valida") is not True]
        tb_ent = [e for e in ent if e.get("ts", 0) >= t_b]
        fallos = [e["text"].strip() for e in tb_ent if "sntp: fallo" in e["text"]]
        inicios = [e["text"].strip() for e in tb_ent if "sntp: inicio" in e["text"]]
        sincs = [e["text"].strip() for e in tb_ent if SINC.search(e["text"])]
        boots = [e["text"].strip() for e in tb_ent if "boot: " in e["text"] and " fw=" in e["text"]]
        c.note("", "## Resultado", "",
               f"- sincronización inicial: `{sinc['text'].strip()}`",
               f"- bloqueo: {est_b['sntp_blocked']} (rules_ok {est_b['rules_ok']}); desbloqueo: {not est_u['sntp_blocked']}",
               f"- en las {BLOQUEO_S // 3600} h: {len(st)} status, {len(falsas)} con hora_valida ≠ true; "
               f"{len(meds)} medidas, {len(sin_ts)} sin ts entero",
               f"- «sntp: inicio» {len(inicios)}: {inicios[:4]}", f"- «sntp: fallo» {len(fallos)}: {fallos[:4]}",
               f"- sincronizaciones durante el bloqueo: {len(sincs)}; arranques: {len(boots)}")
        assert st and not falsas, f"hora_valida dejó de ser true: {falsas[:3]}"
        assert meds and not sin_ts, f"medidas sin ts: {sin_ts[:3]}"
        assert fallos, "ningún «sntp: fallo» en el intento de resincronización"
        assert not sincs, f"sincronizó con SNTP bloqueado: {sincs}"
        assert not boots, f"el nodo se reinició: {boots}"
        c.passed(f"{len(st)} status con hora_valida = true y {len(meds)} medidas con ts en 2 h de bloqueo; "
                 f"{len(fallos)} «sntp: fallo» en la resincronización")
