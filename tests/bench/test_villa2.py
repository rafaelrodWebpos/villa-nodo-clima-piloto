"""Filas de la Fase 2 que desbloquea el banco villa-2 (H-87): bench-serial-write,
bench-mqtt-auth y bench-traffic-capture. Atómicos: cada test graba la imagen de la CI y
aprovisiona contra un AP desechable nuevo con el broker del banco.

TC-TIME-08 · FR-TIME-02 (bench⁺): tras sincronizar, SNTP bloqueado y `reiniciar` por la
  consola → `boot: … reset=sw` y hora_valida = false en los status tras el reinicio.
TC-WDT-02 · NFR-WDT-01 (fila target): `wdt-test` → «wdt: bloqueando medicion» y, en ≤ 32 s,
  `boot: … reset=task_wdt`.
TC-MQTT-05 · FR-MQTT-07: broker con autenticación; con credenciales que no acepta, el DUT
  sigue en CONECTANDO_BROKER con backoff; con las suyas, OPERATIVO.
TC-LOG-08 · FR-LOG-02 (fila de captura): imagen de banco; los datagramas de log van por
  unicast solo a 192.168.4.1:5555.
TC-LOG-04 · FR-LOG-01: imagen de PRODUCCIÓN; en el arranque y 3 ciclos solo DHCP, DNS y SNTP
  por UDP (ninguno al 5555). Se lanza aparte, con --firmware-dir de la imagen de producción."""
import json
import re
import secrets
import time

import pytest

from benchlib import Registro, case
from test_mqtt import _a_operativo, _nodo, _suscribir, configurado

T11 = "con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up)"
SINC = re.compile(r"sntp: sincronizado ts=\d+")
BOOT = re.compile(r"nodo: boot: \S+ fw=\S+ reset=(\w+)")
LOG_HOST, LOG_PORT = "192.168.4.1", 5555
UDP_PERMITIDOS = {53, 67, 68, 123}       # DNS, DHCP y SNTP (FR-LOG-01)


def _escribir(tb, slot, texto):
    r = tb.serial_write(slot, text=texto + "\n")
    assert r.get("ok", True), f"serial_write falló: {r}"


def test_tc_time_08_reboot_without_sntp(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-TIME-08 · FR-TIME-02 — tras reiniciar sin SNTP, hora_valida = false."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    with case(tb, "TC-TIME-08", "Reinicio sin SNTP: hora no válida", run_dir, spec="TC-TIME villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        try:
            with _suscribir(tb, _nodo(dut_mac)) as sub:
                _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
                assert reg.esperar(SINC.pattern, 90), "precondición: sin «sntp: sincronizado»"
                c.step("Bloquear SNTP y enviar «reiniciar» por la consola")
                tb.sntp_block(True)
                t0 = time.time()
                _escribir(tb, dut_slot, "reiniciar")
                boot = reg.esperar(BOOT.pattern, 60, desde_ts=t0)
                assert boot, "sin línea boot: tras «reiniciar»"
                assert reg.esperar(re.escape(T11), 150, desde_ts=t0), "sin T11 tras el reinicio"
                time.sleep(130)                                  # dos status de ciclo
                st = [json.loads(m["payload"]) for m in sub.mensajes()
                      if m["topic"] == f"{base}/status" and not m["retain"] and m["t"] >= t0 and m["payload"]]
                st = [s for s in st if s.get("estado") == "online"]
                txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t0]
        finally:
            tb.sntp_block(False)
        c.save_log("serie", txt)
        reset = BOOT.search(boot["text"]).group(1)
        hv = [s.get("hora_valida") for s in st]
        c.note(f"- boot tras «reiniciar»: reset={reset}", f"- hora_valida en los status tras el reinicio: {hv}",
               f"- «sntp: sincronizado» tras el reinicio: {sum(bool(SINC.search(t)) for t in txt)}")
        assert reset == "sw", f"reset={reset}, esperado sw"
        assert len(hv) >= 2 and not any(hv), f"hora_valida tras el reinicio: {hv}"
        assert not any(SINC.search(t) for t in txt), "se sincronizó con SNTP bloqueado"
        c.passed(f"reset=sw; hora_valida = false en {len(hv)} status sin SNTP")


def test_tc_wdt_02_task_watchdog(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-WDT-02 · NFR-WDT-01 (target) — wdt-test → reset=task_wdt en ≤ 30 s (+ 2 s)."""
    tb = testbench
    with case(tb, "TC-WDT-02", "Watchdog de tareas (wdt-test)", run_dir, spec="TC-WDT villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        _, reg = _a_operativo(tb, dut_slot, banco, c)
        c.step("Enviar «wdt-test» por la consola")
        t0 = time.time()
        _escribir(tb, dut_slot, "wdt-test")
        blq = reg.esperar(re.escape("wdt: bloqueando medicion"), 20, desde_ts=t0)
        assert blq, "sin «wdt: bloqueando medicion»"
        boot = reg.esperar(BOOT.pattern, 60, desde_ts=blq["ts"])
        txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t0]
        c.save_log("serie", txt)
        assert boot, "el nodo quedó colgado: ninguna línea boot: en 60 s"
        dt = boot["ts"] - blq["ts"]                       # marcas del banco (la consola llega al momento)
        reset = BOOT.search(boot["text"]).group(1)
        c.note(f"- de «bloqueando medicion» a la línea boot: {dt:.1f} s; reset={reset}")
        assert reset == "task_wdt", f"reset={reset}"
        assert dt <= 33, f"reinicio a {dt:.1f} s (30 s + 2 s, más el arranque hasta boot:)"
        c.passed(f"reset=task_wdt a {dt:.1f} s de «bloqueando medicion»")


def test_tc_mqtt_05_broker_authentication(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-MQTT-05 · FR-MQTT-07 — credenciales rechazadas: backoff sin OPERATIVO; aceptadas: OPERATIVO."""
    tb = testbench
    usuario, clave, otra = "nodo-prueba", secrets.token_hex(12), secrets.token_hex(12)
    with case(tb, "TC-MQTT-05", "Broker con autenticación", run_dir, spec="TC-MQTT villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path, mqtt_user=usuario, mqtt_pass=clave) as banco:
        c.secretos = list(c.secretos) + [(otra, "<otra-clave-de-prueba>")]
        try:
            c.step("Broker con autenticación que NO acepta las credenciales del DUT; 90 s")
            tb.mqtt_start(usuario, otra)
            banco.broker = True
            t0 = time.time()
            reg = Registro(tb, dut_slot, t0)
            tb.serial_reset(dut_slot)
            banco.ap_on()
            time.sleep(90)
            txt1 = [e.get("text", "") for e in reg.leer()]
            intentos = [t for t in txt1 if re.search(r"nodo: mqtt: intento \d+", t)]
            op1 = [t for t in txt1 if T11 in t]
            c.note(f"- con credenciales rechazadas: {len(intentos)} intentos MQTT, T11: {len(op1)}")
            c.step("Broker con las credenciales del DUT; esperar T11")
            tb.mqtt_stop()
            t1 = time.time()
            tb.mqtt_start(usuario, clave)
            ok = reg.esperar(re.escape(T11), 120, desde_ts=t1)
            txt = [e.get("text", "") for e in reg.leer()]
        finally:
            try:
                tb.mqtt_stop()
            except Exception:
                pass
            banco.broker = False
        c.save_log("serie", txt)
        ms = [int(re.match(r"\s*I \((\d+)\)", t).group(1)) for t in intentos if re.match(r"\s*I \((\d+)\)", t)]
        gaps = [round((b - a) / 1000, 1) for a, b in zip(ms, ms[1:])]
        c.note(f"- intervalos entre intentos (s): {gaps}", f"- con las credenciales aceptadas: T11 {'sí' if ok else 'no'}")
        assert not op1, "llegó a OPERATIVO con credenciales rechazadas"
        assert len(intentos) >= 3 and gaps and gaps[-1] > gaps[0], f"sin backoff creciente: {gaps}"
        assert ok, "sin T11 con las credenciales aceptadas"
        assert not any(clave in t or otra in t for t in txt), "una clave salió por la consola (FR-SEC-03)"
        c.passed(f"rechazadas: {len(intentos)} intentos con backoff {gaps}; aceptadas: OPERATIVO")


def _captura_arranque(tb, dut_slot, dut_mac, banco, c, segundos=240):
    """Arranque y 3 ciclos con la captura en marcha; devuelve los flujos UDP del DUT."""
    banco.broker_on()
    banco.ap_on()
    tb.capture_start(dut_mac.lower(), segundos)
    reg = Registro(tb, dut_slot, time.time())
    tb.serial_reset(dut_slot)
    assert reg.esperar(re.escape(T11), 150), "sin T11"
    fin = time.time() + segundos + 30
    r = {}
    while time.time() < fin:
        r = tb.capture_result()
        if r.get("state") == "done":
            break
        time.sleep(5)
    assert r.get("state") == "done", f"la captura no terminó: {r.get('state')}"
    flujos = r.get("flows") or []
    c.note("", "## Flujos del DUT (captura de cabeceras)", "",
           *[f"- {f['proto']} → {f['dst']}:{f['dport']} ({f['kind']}): {f['packets']}" for f in flujos])
    return [f for f in flujos if f["proto"] == "UDP"], flujos


def test_tc_log_08_udp_log_unicast_only(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-LOG-08 · FR-LOG-02 (captura) — el log UDP va por unicast solo a 192.168.4.1:5555."""
    tb = testbench
    if firmware["variant"] == "production":
        pytest.skip("not done: TC-LOG-08 necesita la imagen de banco")
    with case(tb, "TC-LOG-08", "Log UDP solo por unicast al receptor", run_dir, spec="TC-LOG villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.step("Captura del tráfico del DUT durante el arranque y 3 ciclos")
        udp, _ = _captura_arranque(tb, dut_slot, dut_mac, banco, c)
    log = [f for f in udp if f["dport"] == LOG_PORT]
    malos = [f for f in log if f["dst"] != LOG_HOST or f["kind"] != "unicast"]
    assert log and sum(f["packets"] for f in log) > 10, f"control positivo: casi no hay log UDP: {log}"
    assert not malos, f"log UDP por broadcast o a otro destino: {malos}"
    c.passed(f"{sum(f['packets'] for f in log)} datagramas de log, todos unicast a {LOG_HOST}:{LOG_PORT}")


def test_tc_log_04_no_udp_log_in_production(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-LOG-04 · FR-LOG-01 — imagen de producción: por UDP solo DHCP, DNS y SNTP."""
    tb = testbench
    if firmware["variant"] != "production":
        pytest.skip("not done: TC-LOG-04 necesita la imagen de producción (--firmware-dir)")
    with case(tb, "TC-LOG-04", "Sin log UDP en producción", run_dir, spec="TC-LOG villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.step("Captura del tráfico del DUT durante el arranque y 3 ciclos (imagen de producción)")
        udp, flujos = _captura_arranque(tb, dut_slot, dut_mac, banco, c)
    otros = [f for f in udp if f["dport"] not in UDP_PERMITIDOS]
    assert any(f["proto"] == "TCP" and f["dport"] == 1883 for f in flujos), "control positivo: no se ve el MQTT del DUT"
    assert not otros, f"UDP fuera de DHCP/DNS/SNTP: {otros}"
    c.passed("por UDP solo " + ", ".join(sorted({str(f['dport']) for f in udp})) + "; ningún datagrama al 5555")
