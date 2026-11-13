"""Comprobaciones de las capacidades bench-ap-internet y bench-sntp-block del banco con el fork
propio rafaelrodWebpos/Embedded-AI-Harness (H-72, H-73, H-74). No son tests del FSD: son la
evidencia con la que esas capacidades pasan a `yes` en el plan (como sda-disconnect).

- FORK-01: valores por defecto y reinicio a apagado (sin DUT).
- FORK-02: salida real (el DUT sincroniza SNTP por el AP) y bloqueo de UDP/123 bajo demanda.
- FORK-03: la LAN de la casa queda cerrada: con la salida encendida, el DUT configurado contra
  un broker en la laptop (IP de la LAN) no llega nunca; control positivo: la Pi sí alcanza ese
  puerto y el DUT sí sale a Internet (SNTP) en la misma sesión. Necesita BROKER_LAN_IP (la IP
  de la laptop en la LAN, que nunca entra en la evidencia) y el broker en Docker arrancado.

Ninguna IP de la LAN llega a la evidencia: el prefijo /24 de la red de casa se redacta."""
import json
import os
import re
import time
import urllib.error
import urllib.request

import pytest

from benchlib import Registro, aprovisionar, case, suscriptor_mqtt
from test_mqtt import Banco, _a_operativo, _nodo, _suscribir, configurado, grabar

PRIVADOS = ("0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16",
            "172.16.0.0/12", "192.168.0.0/16", "224.0.0.0/4", "240.0.0.0/4")
SNTP_DROP = "-A HARNESS_AP_FWD -p udp -m udp --dport 123 -j DROP"
SINCRONIZADO = re.compile(r"sntp: sincronizado ts=(\d+)")


def _url():
    return os.environ["TESTBENCH_URL"].rstrip("/")


def _prefijo_casa():
    m = re.search(r"//(\d+\.\d+\.\d+)\.\d+", os.environ.get("TESTBENCH_URL", ""))
    return m.group(1) + "." if m else None


def _redactar_casa(c):
    p = _prefijo_casa()
    if p:
        c.secretos = list(getattr(c, "secretos", [])) + [(p, "<red-casa>.")]
    ip = os.environ.get("BROKER_LAN_IP")
    if ip:
        c.secretos = list(c.secretos) + [(ip, "<ip-laptop>")]


def _api(method, path, body=None, timeout=20):
    """Petición cruda: devuelve (código HTTP, JSON). El driver del contenedor aún no trae
    los métodos del fork."""
    data = json.dumps(body).encode() if body is not None else None
    cab = {"Content-Type": "application/json"} if data else {}
    if os.environ.get("TESTBENCH_TOKEN"):                 # villa-2 (S6-01): token de la API
        cab["X-Harness-Token"] = os.environ["TESTBENCH_TOKEN"]
    req = urllib.request.Request(_url() + path, data=data, method=method, headers=cab)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def _estado():
    code, st = _api("GET", "/api/wifi/internet")
    assert code == 200 and st.get("ok"), f"GET /api/wifi/internet → {code} {st}"
    return st


def _internet(on):
    code, st = _api("POST", "/api/wifi/internet", {"enabled": on})
    assert code == 200 and st.get("ok"), f"POST internet {on} → {code} {st}"
    return st


def _sntp_block(on):
    code, st = _api("POST", "/api/wifi/sntp_block", {"blocked": on})
    assert code == 200 and st.get("ok"), f"POST sntp_block {on} → {code} {st}"
    return st


def _resumen(st):
    return (f"internet={st['internet']} sntp_blocked={st['sntp_blocked']} lan_blocked={st['lan_blocked']} "
            f"rules_ok={st['rules_ok']} reglas={len(st['rules'])}")


def test_fork_01_defaults_and_reset(testbench, run_dir):
    """FORK-01 — capacidades reportadas; apagado por defecto; encendido con todos los rangos
    privados cortados; bloqueo de SNTP antes de cualquier ACCEPT; cuerpos que no son booleanos
    rechazados; ap_stop devuelve todo a apagado; rules_ok en cada paso."""
    tb = testbench
    with case(tb, "FORK-01", "Salida del AP: valores por defecto y reinicio", run_dir,
              spec="banco con el fork villa-1") as c:
        _redactar_casa(c)
        code, info = _api("GET", "/api/info")
        c.note(f"- /api/info: build={info.get('build')}, capabilities={info.get('capabilities')}", "")
        assert {"bench-ap-internet", "bench-sntp-block"} <= set(info.get("capabilities") or []), info
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro"
        pasos = []
        c.step("Estado inicial")
        st = _estado(); pasos.append(("inicial", st))
        assert not st["internet"] and not st["sntp_blocked"] and st["rules_ok"]
        assert st["rules"] == ["-N HARNESS_AP_FWD", "-A HARNESS_AP_FWD -j DROP"], st["rules"]

        c.step("Cuerpos inválidos: {\"enabled\": \"false\"}, {\"enabled\": 1}, {} → 400 y sin cambios")
        for body in ({"enabled": "false"}, {"enabled": 1}, {}):
            code, r = _api("POST", "/api/wifi/internet", body)
            pasos.append((f"POST {json.dumps(body)} → {code}", _estado()))
            assert code == 400 and not r.get("ok"), (body, code, r)
        assert not _estado()["internet"]
        try:
            c.step("Encender la salida (sin AP)")
            st = _internet(True); pasos.append(("encendida", st))
            assert st["internet"] and st["rules_ok"] and st["lan_blocked"]
            for net in PRIVADOS:
                assert f"-A HARNESS_AP_FWD -d {net} -j DROP" in st["rules"], net
            i_up = st["rules"].index("-A HARNESS_AP_FWD -o eth0 -j ACCEPT")
            assert all(st["rules"].index(f"-A HARNESS_AP_FWD -d {n} -j DROP") < i_up for n in PRIVADOS)
            assert st["rules"][-1] == "-A HARNESS_AP_FWD -j DROP"

            c.step("Bloquear SNTP")
            st = _sntp_block(True); pasos.append(("sntp bloqueado", st))
            assert st["sntp_blocked"] and st["rules_ok"] and SNTP_DROP in st["rules"]
            primer_accept = next(k for k, r in enumerate(st["rules"])
                                 if r.endswith("-j ACCEPT") and "conntrack" not in r)
            assert st["rules"].index(SNTP_DROP) < primer_accept

            c.step("Levantar un AP de prueba y pararlo: ap_stop devuelve todo a apagado")
            tb.ap_start("fork01-prueba", "clave-fork01", channel=1)
            ap = tb.ap_status()
            pasos.append(("tras ap_start", _estado()))
            assert ap.get("internet") is False and ap.get("sntp_blocked") is False, ap
            tb.ap_stop()
            st = _estado(); pasos.append(("tras ap_stop", st))
            assert not st["internet"] and not st["sntp_blocked"] and st["rules_ok"]
            assert st["rules"] == ["-N HARNESS_AP_FWD", "-A HARNESS_AP_FWD -j DROP"]

            c.step("Encender y apagar: rules_ok en cada paso")
            for on in (True, False, True, False):
                st = _internet(on); pasos.append((f"internet {on}", st))
                assert st["internet"] is on and st["rules_ok"]
        finally:
            if tb.ap_status().get("active"):
                tb.ap_stop()
            _api("POST", "/api/wifi/sntp_block", {"blocked": False})
            _api("POST", "/api/wifi/internet", {"enabled": False})
        c.note("", "## Resultado", "", *[f"- {n}: {_resumen(s)}" for n, s in pasos],
               "", "Reglas con la salida encendida y SNTP bloqueado:", "",
               *[f"    {r}" for r in next(s for n, s in pasos if n == "sntp bloqueado")["rules"]])
        c.passed("capacidades reportadas; apagado por defecto y tras ap_stop; rangos privados cortados; "
                 "SNTP antes de cualquier ACCEPT; cuerpos no booleanos → 400; rules_ok en todos los pasos")


def _esperar_regex(reg, rx, desde, timeout):
    fin = time.time() + timeout
    while time.time() < fin:
        hit = next((e for e in reg.leer() if e.get("ts", 0) >= desde and rx.search(e.get("text", ""))), None)
        if hit:
            return hit
        time.sleep(1)
    return None


def test_fork_02_internet_and_sntp_block(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """FORK-02 — DUT en OPERATIVO con el broker del banco. Salida encendida: «sntp: sincronizado»
    en ≤ 90 s, status hora_valida = true y medidas con ts real (± 10 s del reloj de la laptop).
    Con SNTP bloqueado y el DUT reiniciado: ninguna sincronización en 75 s, «sntp: fallo» y
    hora_valida = false. Desbloqueado: sincroniza en ≤ 40 s."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "FORK-02", "Salida a Internet real y bloqueo de SNTP", run_dir,
              spec="banco con el fork villa-1") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        _redactar_casa(c)
        banco.broker_on()
        res = {}
        try:
            with _suscribir(tb, nodo) as sub:
                t0, reg = _a_operativo(tb, dut_slot, banco, c)
                c.step("Encender la salida a Internet del AP")
                t_on = time.time()
                res["estado_on"] = _internet(True)
                hit = _esperar_regex(reg, SINCRONIZADO, t_on - 2, 90)
                res["sinc"] = (hit["text"].strip(), hit["ts"] - t_on) if hit else None
                c.step("Esperar un status y una medida con hora")
                fin = time.time() + 75
                st_ok = med_ok = None
                while time.time() < fin and not (st_ok and med_ok):
                    for m in sub.mensajes():
                        if m["t"] < t_on or m["retain"] or not m["payload"]:
                            continue
                        try:
                            p = json.loads(m["payload"])
                        except ValueError:
                            continue
                        if m["topic"] == f"{base}/status" and p.get("hora_valida") is True:
                            st_ok = st_ok or (m, p)
                        if m["topic"] == f"{base}/temperatura" and isinstance(p.get("ts"), int):
                            med_ok = med_ok or (m, p)
                    time.sleep(1)
                res["status_hora"], res["medida_ts"] = st_ok, med_ok

                c.step("Bloquear SNTP y reiniciar el DUT")
                res["estado_block"] = _sntp_block(True)
                t_b = time.time()
                tb.serial_reset(dut_slot)
                time.sleep(75)
                ent = reg.leer()
                res["fallos_block"] = [e["text"].strip() for e in ent if e.get("ts", 0) >= t_b and "sntp: fallo" in e["text"]]
                res["sinc_block"] = [e["text"].strip() for e in ent if e.get("ts", 0) >= t_b and SINCRONIZADO.search(e["text"])]
                res["status_block"] = [json.loads(m["payload"]).get("hora_valida") for m in sub.mensajes()
                                       if m["t"] >= t_b + 20 and m["topic"] == f"{base}/status" and not m["retain"]
                                       and '"online"' in m["payload"]]

                c.step("Desbloquear SNTP")
                t_u = time.time()
                res["estado_unblock"] = _sntp_block(False)
                hit = _esperar_regex(reg, SINCRONIZADO, t_u - 1, 40)
                res["sinc_unblock"] = (hit["text"].strip(), hit["ts"] - t_u) if hit else None
                msgs = sub.mensajes()
        finally:
            _api("POST", "/api/wifi/sntp_block", {"blocked": False})
            _api("POST", "/api/wifi/internet", {"enabled": False})
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])
        sm, mm = res["status_hora"], res["medida_ts"]
        c.note("", "## Resultado", "",
               f"- salida encendida: {_resumen(res['estado_on'])}",
               f"- sincronización: " + (f"`{res['sinc'][0]}` a {res['sinc'][1]:.1f} s de encender la salida" if res["sinc"] else "ninguna en 90 s"),
               f"- status con hora_valida = true: " + (f"a {sm[0]['t'] - t_on:+.1f} s" if sm else "ninguno"),
               f"- medida con ts: " + (f"`{mm[0]['payload']}`, desfase {mm[1]['ts'] - mm[0]['t']:+.1f} s respecto a la llegada" if mm else "ninguna"),
               f"- SNTP bloqueado: {_resumen(res['estado_block'])}; tras reiniciar el DUT, 75 s: "
               f"{len(res['fallos_block'])} «sntp: fallo», {len(res['sinc_block'])} sincronizaciones, "
               f"hora_valida en los status: {res['status_block']}",
               f"- SNTP desbloqueado: " + (f"`{res['sinc_unblock'][0]}` a {res['sinc_unblock'][1]:.1f} s" if res["sinc_unblock"] else "sin sincronizar en 40 s"))
        assert res["estado_on"]["internet"] and res["estado_on"]["rules_ok"]
        assert res["sinc"], "el DUT no sincronizó SNTP con la salida encendida"
        assert sm, "ningún status con hora_valida = true"
        assert mm and abs(mm[1]["ts"] - mm[0]["t"]) <= 10, f"ts de la medida fuera de ± 10 s: {mm}"
        assert res["estado_block"]["sntp_blocked"] and res["estado_block"]["rules_ok"]
        assert not res["sinc_block"], f"sincronizó con SNTP bloqueado: {res['sinc_block']}"
        assert len(res["fallos_block"]) >= 1, "ningún «sntp: fallo» con SNTP bloqueado"
        assert res["status_block"] and not any(res["status_block"]), f"hora_valida con SNTP bloqueado: {res['status_block']}"
        assert res["sinc_unblock"], "no sincronizó al desbloquear SNTP"
        c.passed(f"sincroniza a {res['sinc'][1]:.1f} s de encender la salida; con SNTP bloqueado 0 sincronizaciones y "
                 f"{len(res['fallos_block'])} fallos; desbloqueado sincroniza a {res['sinc_unblock'][1]:.1f} s")


@pytest.mark.skipif(not os.environ.get("BROKER_LAN_IP"), reason="sin BROKER_LAN_IP (broker en la laptop)")
def test_fork_03_lan_stays_closed(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """FORK-03 — prueba negativa de la LAN (H-73). DUT configurado contra un broker en la laptop
    (IP de la LAN), salida encendida, broker del banco parado: en 180 s ningún mensaje del DUT
    llega al broker de la laptop, mientras el DUT sí sincroniza SNTP (salida activa). Control
    positivo: el broker de la laptop recibe por la LAN (relé HTTP del banco desde la Pi; se
    comprueba fuera, en su log) y el suscriptor del test lo alcanza por esa misma IP."""
    tb = testbench
    lan_ip = os.environ["BROKER_LAN_IP"]
    nodo = _nodo(dut_mac)
    with case(tb, "FORK-03", "La LAN de la casa queda cerrada", run_dir, spec="banco con el fork villa-1") as c:
        _redactar_casa(c)
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})",
               "- broker de prueba en Docker en la laptop, en su IP de la LAN (<ip-laptop>), puerto 1883", "")
        c.step(f"Precondiciones: grabar la imagen; aprovisionar el DUT con el broker de la laptop")
        grabar(tb, dut_slot, firmware, c)
        ssid, clave = aprovisionar(tb, dut_slot, nodo, c, tmp_path, mqtt_host=lan_ip)
        assert not tb.mqtt_status().get("running"), "el broker del banco está activo: no es nuestro"
        banco = Banco(tb, ssid, clave)
        res = {}
        try:
            with suscriptor_mqtt(_BrokerLaptop(lan_ip), ["#"]) as sub_lan:
                c.step("Control positivo: la Pi abre una conexión al broker de la laptop por la LAN (relé HTTP)")
                t_ctrl = time.time()
                try:
                    tb.wifi_http(f"http://{lan_ip}:1883/", timeout=5)
                    res["relay"] = "respuesta"
                except Exception as e:
                    res["relay"] = type(e).__name__
                res["t_ctrl"] = t_ctrl
                c.step("Resetear el DUT, levantar el AP y encender la salida a Internet")
                t0 = time.time()
                reg = Registro(tb, dut_slot, t0)
                tb.serial_reset(dut_slot)
                banco.ap_on()
                res["estado"] = _internet(True)
                t_on = time.time()
                c.step("Observar 180 s")
                time.sleep(180)
                res["sinc"] = next((e["text"].strip() for e in reg.leer()
                                    if e.get("ts", 0) >= t0 and SINCRONIZADO.search(e["text"])), None)
                res["estado_fin"] = _estado()
                lan = [m for m in sub_lan.mensajes() if m["t"] >= t0 and nodo in m["topic"]]
                res["lan"] = lan
                res["conexiones_sub"] = len(sub_lan.conexiones)
        finally:
            banco.limpiar()
            _api("POST", "/api/wifi/internet", {"enabled": False})
        ent = reg.leer()
        mqtt_err = [e["text"].strip() for e in ent if e.get("ts", 0) >= t0 and re.search(r"mqtt|CONECTANDO_BROKER", e["text"])]
        c.save_log("serie", [e["text"] for e in ent])
        c.note("", "## Resultado", "",
               f"- salida encendida durante la ventana: {_resumen(res['estado'])}; al final: {_resumen(res['estado_fin'])}",
               f"- relé HTTP del banco hacia <ip-laptop>:1883 (control, ver log del broker): {res['relay']}",
               f"- suscriptor del test conectado al broker de la laptop: {res['conexiones_sub']} vez/veces",
               f"- SNTP del DUT en la misma sesión: " + (f"`{res['sinc']}`" if res["sinc"] else "sin sincronizar"),
               f"- mensajes del DUT en el broker de la laptop: {len(res['lan'])}",
               f"- líneas de la consola sobre el broker (las 5 primeras): {mqtt_err[:5]}")
        assert res["conexiones_sub"] >= 1, "el suscriptor no alcanzó el broker de la laptop: control inválido"
        assert res["estado"]["internet"] and res["estado"]["rules_ok"]
        assert res["sinc"], "el DUT no sincronizó SNTP: la salida no estaba activa, la prueba no prueba nada"
        assert not res["lan"], f"el DUT llegó al broker de la LAN: {len(res['lan'])} mensajes"
        c.passed("con la salida encendida el DUT sale a Internet (SNTP) y no llega al broker de la LAN en 180 s")


class _BrokerLaptop:
    """Adaptador mínimo para suscriptor_mqtt: el broker es la laptop, no el banco."""

    def __init__(self, ip):
        self.base_url = f"http://{ip}"
