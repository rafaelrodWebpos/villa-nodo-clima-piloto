"""Fase 3 — adaptador OTA, filas de banco sin descarga (no necesitan Internet ni el banco
nuevo). Atómicos: cada test graba la imagen de la CI, aprovisiona contra un AP desechable
nuevo con el broker del banco y deja el nodo en OPERATIVO.

TC-OTA-06 · T18, FR-OTA-09, FR-MQTT-09 (fila 1): comandos OTA que incumplen la guarda de
T17 → `status` en vivo con `ota` = rechazado:<payload|host|ruta> en ≤ 2 s, su E7 y su E0
(«con: OPERATIVO -> OPERATIVO (cmd_ota)»), sin pasar nunca a OTA_DESCARGA.

TC-OTA-07 · FR-OTA-04: un comando válido publicado con retain mientras el DUT está sin
conexión (AP del banco apagado) se ignora al reconectar: E8 «ota: ignorado retained», sin
E7, sin OTA_DESCARGA y `ota` sigue en «ninguno»."""
import json
import os
import re
import time

import pytest

from benchlib import case
from test_mqtt import _a_operativo, _nodo, _suscribir, configurado

REPO = "https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/"
PLAZO_S = 2.0                     # FR-MQTT-09
CASOS = [                         # (payload, ota esperado)
    (b"no-json", "rechazado:payload"),
    (json.dumps({"url": "http://github.com/x"}).encode(), "rechazado:host"),
    (json.dumps({"url": "https://github.com/otro/repo/releases/download/v1/x.bin"}).encode(), "rechazado:ruta"),
]
DESCARGA = "-> OTA_DESCARGA"


def _publicar(tb, topico, payload, retain=False):
    import paho.mqtt.client as mqtt
    from urllib.parse import urlparse
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"banco-pub-{os.getpid()}-{time.time_ns() % 10**6}")
    cli.connect(urlparse(tb.base_url).hostname, 1883, keepalive=30)
    cli.loop_start()
    try:
        t0 = time.time()                    # antes de publicar: el DUT responde en ms, antes que el cierre
        cli.publish(topico, payload, qos=1, retain=retain).wait_for_publish(5)
    finally:
        cli.loop_stop()
        cli.disconnect()
    return t0


def _status(msgs, base, desde):
    for m in msgs:
        if m["topic"] == f"{base}/status" and not m["retain"] and m["t"] >= desde and m["payload"]:
            try:
                yield m["t"], json.loads(m["payload"])
            except ValueError:
                continue


def test_tc_ota_06_rejections(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-06 · T18, FR-OTA-09, FR-MQTT-09 — rechazos por payload, host y ruta en ≤ 2 s."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-OTA-06", "Rechazos de comandos OTA (T18)", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c)
            time.sleep(3)
            resultados = []
            for payload, esperado in CASOS:
                c.step(f"Publicar en cmd/ota un comando que debe dar {esperado}")
                t_pub = _publicar(tb, f"{base}/cmd/ota", payload)
                llegada = None
                fin = time.time() + 10
                while llegada is None and time.time() < fin:
                    llegada = next(((t, st) for t, st in _status(sub.mensajes(), base, t_pub)
                                    if st.get("ota") == esperado), None)
                    time.sleep(0.2)
                ok_e7 = reg.esperar(re.escape(f"ota: estado {esperado}"), 15, desde_ts=t_pub - 1) is not None
                ok_e0 = reg.esperar(re.escape("con: OPERATIVO -> OPERATIVO (cmd_ota)"), 15, desde_ts=t_pub - 1) is not None
                dt = None if llegada is None else llegada[0] - t_pub
                resultados.append((esperado, dt, ok_e7, ok_e0))
                c.note(f"- {esperado}: status a " + ("—" if dt is None else f"{dt:.2f} s") +
                       f"; E7 {'sí' if ok_e7 else 'no'}; E0 {'sí' if ok_e0 else 'no'}")
                time.sleep(2)
            ent = reg.leer()
        txt = [e.get("text", "") for e in ent]
        c.save_log("serie", txt)
        descarga = [t for t in txt if DESCARGA in t]
        assert not descarga, f"pasó a OTA_DESCARGA: {descarga[:1]}"
        for esperado, dt, ok_e7, ok_e0 in resultados:
            assert dt is not None, f"ningún status con ota={esperado}"
            assert dt <= PLAZO_S, f"{esperado}: status a {dt:.2f} s (FR-MQTT-09: ≤ {PLAZO_S} s)"
            assert ok_e7 and ok_e0, f"{esperado}: falta E7 o E0"
        c.passed("rechazado:payload, :host y :ruta en " + ", ".join(f"{dt:.2f} s" for _, dt, _, _ in resultados)
                 + "; E7 y E0 en los tres; sin OTA_DESCARGA")


def test_tc_ota_07_retained_command_ignored(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-07 · FR-OTA-04 — un comando retained se ignora al reconectar (E8)."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    topico = f"{base}/cmd/ota"
    with case(tb, "TC-OTA-07", "Comando OTA retained ignorado", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        try:
            with _suscribir(tb, nodo) as sub:
                _, reg = _a_operativo(tb, dut_slot, banco, c)
                c.step("Apagar el AP del banco (el DUT pierde la conexión; el broker sigue)")
                banco.ap_off()
                time.sleep(5)
                c.step("Publicar con retain un comando válido (URL de una release v*)")
                _publicar(tb, topico, json.dumps({"url": REPO + "v0.0.1/firmware_v0.0.1.bin"}).encode(), retain=True)
                c.step("Encender el AP; esperar la reconexión (T11) y la entrega del retenido")
                t_on = time.time()
                banco.ap_on()
                assert reg.esperar(re.escape("con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up)"), 150, desde_ts=t_on), "sin T11 tras volver el AP"
                e8 = reg.esperar(re.escape("ota: ignorado retained"), 30, desde_ts=t_on)
                time.sleep(65)                              # un status de ciclo después
                txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t_on]
                otas = [st.get("ota") for _, st in _status(sub.mensajes(), base, t_on)
                        if st.get("estado") == "online"]          # el Last Will («offline») no lleva ota
            c.save_log("serie", txt)
            e7 = [t for t in txt if "ota: estado" in t]
            descarga = [t for t in txt if DESCARGA in t]
            c.note(f"- E8: {'sí' if e8 else 'no'}; E7: {len(e7)}; OTA_DESCARGA: {len(descarga)}; ota en status: {sorted(set(otas))}")
            assert e8, "sin «ota: ignorado retained» (E8)"
            assert not e7 and not descarga, "el comando retained se procesó"
            assert otas and set(otas) == {"ninguno"}, f"ota en status: {otas}"
        finally:
            _publicar(tb, topico, b"", retain=True)        # borrar el retenido
        c.passed("retenido ignorado con E8 al reconectar; sin E7 ni OTA_DESCARGA; ota = ninguno")
