"""TC-MQTT-03, TC-CON-08/09/10 — publicador MQTT y gestor de conectividad con el AP y el
broker reales del banco (FSD §6.6, §9.5, §10.4; Fase 2). Atómicos: cada uno graba la
imagen de la CI, aprovisiona contra un AP desechable nuevo y deja el AP y el broker
apagados al terminar."""
import contextlib
import json
import re
import time

import pytest

from benchlib import (Registro, _parse_flash_args, aprovisionar, case, suscriptor_mqtt,
                      ultimo_arranque)

BROKER_BANCO = "192.168.4.1"                        # el broker del banco visto desde su AP
BACKOFF_S = [1, 2, 4, 8, 16, 32, 60, 60, 60, 60]    # FR-CON-02
TOLERANCIA = 0.10
T11_ESPERA_S = 60
LWT = '{"estado":"offline"}'
MEDIDAS = ("temperatura", "humedad", "punto_rocio")
T11 = "con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up)"


def _ms(texto):
    m = re.match(r"\s*\w \((\d+)\)", texto)
    return int(m.group(1)) if m else None


def _nodo(dut_mac):
    return "clima-" + dut_mac.replace(":", "").lower()[-6:]


def _discovery_esperado(nodo, medida, fw):
    """§10.2 con sitio1/zona1 (los de aprovisionar)."""
    nombre, clase, unidad = {"temperatura": ("Temperatura", "temperature", "°C"),
                             "humedad": ("Humedad", "humidity", "%"),
                             "punto_rocio": ("Punto de rocío", "temperature", "°C")}[medida]
    base = f"sitio1/zona1/{nodo}"
    return {"name": nombre, "unique_id": f"{nodo}_{medida}", "state_topic": f"{base}/{medida}",
            "value_template": "{{ value_json.v }}", "unit_of_measurement": unidad,
            "device_class": clase, "state_class": "measurement", "expire_after": 180,
            "availability_topic": f"{base}/status", "availability_template": "{{ value_json.estado }}",
            "payload_available": "online", "payload_not_available": "offline",
            "device": {"identifiers": [nodo], "name": "Clima sitio1 zona1",
                       "model": "Waveshare ESP32-S3-DEV-KIT-N8R8 + SHT41", "sw_version": fw}}


class Banco:
    """AP y broker que el test enciende; al salir, apaga solo lo que encendió."""

    def __init__(self, tb, ssid, clave):
        self.tb, self.ssid, self.clave = tb, ssid, clave
        self.ap = self.broker = False

    def ap_on(self):
        self.tb.ap_start(self.ssid, self.clave, channel=1); self.ap = True

    def ap_off(self):
        self.tb.ap_stop(); self.ap = False

    def broker_on(self):
        self.tb.mqtt_start(); self.broker = True

    def broker_off(self):
        self.tb.mqtt_stop(); self.broker = False

    def limpiar(self):
        if self.ap:
            self.ap_off()
        if self.broker:
            self.broker_off()


PUERTO_OCUPADO = "Could not exclusively lock port"
ESPERA_PUERTO_S = 15        # H-61


def grabar(tb, slot, firmware, c):
    """Graba la imagen de la CI. Si el banco tiene el puerto serie ocupado (CR-TB-13, tras un
    desenchufe y reenchufe del USB-C), espera 15 s y reintenta una vez; si sigue, not done."""
    args = _parse_flash_args(firmware["dir"] / "coldflash")
    res = tb.flash(slot, args, chip="esp32s3")
    if not res.get("ok") and PUERTO_OCUPADO in str(res.get("output", "")):
        c.note(f"- el banco tenía el puerto serie ocupado al grabar (CR-TB-13); reintento en {ESPERA_PUERTO_S} s")
        time.sleep(ESPERA_PUERTO_S)
        res = tb.flash(slot, args, chip="esp32s3")
        if not res.get("ok") and PUERTO_OCUPADO in str(res.get("output", "")):
            pytest.skip("not done: el banco mantiene ocupado el puerto serie tras reintentar (CR-TB-13)")
    assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"


@contextlib.contextmanager
def configurado(tb, slot, dut_mac, firmware, c, tmp_path):
    """Precondición: imagen de la CI grabada y DUT aprovisionado con el broker del banco;
    AP y broker apagados. Devuelve el Banco, que se limpia al salir."""
    c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})",
           f"- broker del banco (abierto); tópicos bajo `sitio1/zona1/{_nodo(dut_mac)}/` y "
           f"`homeassistant/sensor/{_nodo(dut_mac)}/`", "")
    c.step(f"Precondiciones: grabar la imagen de la CI en {slot}")
    grabar(tb, slot, firmware, c)
    ssid, clave = aprovisionar(tb, slot, _nodo(dut_mac), c, tmp_path, mqtt_host=BROKER_BANCO)
    assert not tb.mqtt_status().get("running"), "el broker del banco está activo: no es nuestro, no se toca"
    banco = Banco(tb, ssid, clave)
    try:
        yield banco
    finally:
        banco.limpiar()


def _suscribir(tb, nodo):
    base = f"sitio1/zona1/{nodo}"
    return suscriptor_mqtt(tb, [f"{base}/#", f"homeassistant/sensor/{nodo}/#"],
                           limpiar=[f"{base}/{m}" for m in ("status",) + MEDIDAS] +
                                   [f"homeassistant/sensor/{nodo}/{m}/config" for m in MEDIDAS])


def _a_operativo(tb, slot, banco, c):
    """Broker ya arriba: reset y AP arriba; espera T11. Devuelve (t0, Registro)."""
    c.step("Resetear el DUT y levantar el AP desechable (canal 1); esperar T11")
    t0 = time.time()
    reg = Registro(tb, slot, t0)
    tb.serial_reset(slot)
    banco.ap_on()
    if not reg.esperar(re.escape(T11), T11_ESPERA_S):
        pytest.fail(f"sin {T11} en {T11_ESPERA_S} s")
    return t0, reg


def _ultimo_arranque(reg):
    ent = reg.leer()
    ult = ultimo_arranque(ent)
    assert ult is not None, "la captura no contiene el inicio del arranque tras el reset"
    return ent[ult:]


def _guardar(c, ent, msgs, t0):
    c.save_log("serie", [e["text"] for e in ent])
    c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                        for m in msgs])


def _del_nodo(msgs, nodo, desde):
    """Mensajes en vivo (retain = 0) del nodo o de su Discovery con payload, desde `desde`."""
    return [m for m in msgs if m["t"] >= desde and not m["retain"] and m["payload"]
            and (m["topic"].startswith(f"sitio1/zona1/{nodo}/") or m["topic"].startswith(f"homeassistant/sensor/{nodo}/"))]


def _sin_reinicio(ent):
    e1 = [e["text"] for e in ent if "boot: " in e["text"] and " fw=" in e["text"]]
    assert len(e1) <= 1, f"el nodo se reinició: {e1}"


def test_tc_mqtt_03_connect_order_and_retain(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-MQTT-03 · FR-HA-01, FR-MQTT-04 — broker limpio y DUT que conecta: status, luego las
    tres configuraciones de Discovery (§10.2, retain, QoS 1), luego las medidas; un suscriptor
    nuevo recibe con retain = 1 las configuraciones y el último valor de cada medida."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-MQTT-03", "Orden de conexión y retenidos", run_dir, spec="TC-MQTT villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.step("Arrancar el broker, borrar los retenidos del nodo y suscribirse")
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            c.step("Esperar un ciclo de medición en vivo (70 s)")
            time.sleep(70)
            vivo = sub.mensajes()
        c.step("Suscriptor nuevo: configuraciones y medidas retenidas")
        with suscriptor_mqtt(tb, [f"{base}/#", f"homeassistant/sensor/{nodo}/#"]) as sub2:
            time.sleep(3)
            retenido = sub2.mensajes()
        ent = _ultimo_arranque(reg)
        _guardar(c, ent, vivo + retenido, t0)

        del_nodo = _del_nodo(vivo, nodo, t0)
        temas = [m["topic"].replace(base, "<base>").replace(f"homeassistant/sensor/{nodo}", "<ha>") for m in del_nodo]
        c.note("", "## Resultado", "", f"- secuencia en vivo: {temas[:10]}")
        assert del_nodo and del_nodo[0]["topic"] == f"{base}/status", f"el primero no es status: {temas[:3]}"
        st = json.loads(del_nodo[0]["payload"])
        assert st.get("estado") == "online", f"el primer status no es online: {st}"
        cfg = [i for i, m in enumerate(del_nodo) if m["topic"].endswith("/config")]
        med = [i for i, m in enumerate(del_nodo) if m["topic"].rsplit("/", 1)[-1] in MEDIDAS]
        assert len(cfg) >= 3, f"solo {len(cfg)} configuraciones de Discovery (FR-HA-01)"
        assert med, "ninguna medida en vivo"
        assert cfg[:3] == [1, 2, 3], f"Discovery no va justo después de status: posiciones {cfg[:3]} (FR-HA-01)"
        assert max(cfg[:3]) < med[0], "una medida antes que Discovery (FR-HA-01)"
        for i in cfg[:3]:
            m = del_nodo[i]
            medida = m["topic"].split("/")[-2]
            assert m["topic"] == f"homeassistant/sensor/{nodo}/{medida}/config", f"tópico {m['topic']}"
            assert m["qos"] == 1, f"{m['topic']} con QoS {m['qos']} (§10.2: QoS 1)"
            got, exp = json.loads(m["payload"]), _discovery_esperado(nodo, medida, st["fw"])
            assert got == exp, f"{medida}: Discovery distinto de §10.2: {got}"
        for i in med:
            assert del_nodo[i]["qos"] == 0, f"{del_nodo[i]['topic']} con QoS {del_nodo[i]['qos']} (FR-MQTT-04: QoS 0)"
        # FR-MQTT-04: el suscriptor nuevo recibe, retenido, el último valor en vivo de cada medida
        ret = {m["topic"]: m for m in retenido if m["payload"]}
        for medida in MEDIDAS:
            vivos = [del_nodo[i] for i in med if del_nodo[i]["topic"] == f"{base}/{medida}"]
            assert vivos, f"{medida}: ninguna publicación en vivo"
            r = ret.get(f"{base}/{medida}")
            assert r and r["retain"], f"{medida}: el suscriptor nuevo no la recibió retenida (FR-MQTT-04)"
            assert r["payload"] == vivos[-1]["payload"], f"{medida}: retenido {r['payload']} ≠ último {vivos[-1]['payload']}"
        for medida in MEDIDAS:
            r = ret.get(f"homeassistant/sensor/{nodo}/{medida}/config")
            assert r and r["retain"], f"Discovery de {medida} no quedó retenido (FR-HA-01)"
        _sin_reinicio(ent)
        c.passed("status → 3 configuraciones (§10.2, QoS 1) → medidas (QoS 0); configuraciones y último valor retenidos")


def test_tc_con_08_broker_outage(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-08 · T15, T12, T13, FR-CON-02 (fila MQTT), FR-CON-04, FR-MQTT-06 — en OPERATIVO se
    detiene el broker hasta 10 intervalos del backoff MQTT con el Wi-Fi activo y se vuelve a
    arrancar: T15, T12/T13 con 1, 2, 4 … 60 s ± 10 %, sin tocar el Wi-Fi ni reiniciar; al
    volver, el primer mensaje es status online y una medida válida llega en ≤ 75 s."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-CON-08", "Corte del broker", run_dir, spec="TC-CON villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            time.sleep(5)
            c.step("Detener el broker hasta «mqtt: intento 10» y su fallo (≈ 4 min)")
            t_stop = time.time()
            banco.broker_off()
            i10 = reg.esperar(r"mqtt: intento 10\b", sum(BACKOFF_S[:9]) + 90, desde_ts=t_stop)
            f10 = i10 and reg.esperar(r"-> CONECTANDO_BROKER \(mqtt_down\)", 30, desde_ts=i10["ts"])
            assert f10, "no se llegó a «mqtt: intento 10» y su fallo con el broker parado"
            c.step("Arrancar el broker (el siguiente intento llega a los 60 s)")
            t_start = time.time()
            banco.broker_on()
            # La captura serie del banco puede retener la última línea hasta que llega más
            # salida (T11 llegó 48 s tarde el 2026-11-07; por UDP, a su hora): 150 s cubren el
            # med: del ciclo siguiente. FR-CON-04 y FR-MQTT-06 se miden en el broker.
            vuelta = reg.esperar(re.escape(T11), 150, desde_ts=t_start)
            time.sleep(10)
            msgs = sub.mensajes()
            resus = [t for t in sub.conexiones if t >= t_start]
        ent = _ultimo_arranque(reg)
        _guardar(c, ent, msgs, t0)
        textos = [e["text"] for e in ent]
        t15 = [i for i, t in enumerate(textos) if "con: OPERATIVO -> CONECTANDO_BROKER (mqtt_down)" in t]
        assert len(t15) == 1, f"T15 aparece {len(t15)} veces"
        ventana = textos[t15[0]:]
        # FR-CON-02 (MQTT): de cada «-> CONECTANDO_BROKER (mqtt_down)» al siguiente «mqtt: intento»
        intervalos = []
        for i, t in enumerate(ventana):
            if "-> CONECTANDO_BROKER (mqtt_down)" in t and len(intervalos) < len(BACKOFF_S):
                sig = next((u for u in ventana[i + 1:] if "mqtt: intento " in u), None)
                if sig is None:
                    break
                intervalos.append(round((_ms(sig) - _ms(t)) / 1000, 2))
        t12 = sum("con: CONECTANDO_BROKER -> CONECTANDO_BROKER (mqtt_down)" in t for t in ventana)
        t13 = [i for i, t in enumerate(ventana) if "con: CONECTANDO_BROKER -> CONECTANDO_BROKER (backoff)" in t]
        # T13: el intento sale en el mismo instante que su línea (el firmware escribe E0 tras
        # ejecutar la acción, así que «mqtt: intento» va justo antes): el más cercano, ≤ 1 s;
        # nunca dos intentos sin un resultado entre ellos
        t13_ms = []
        ms_intentos = [_ms(t) for t in ventana if "mqtt: intento " in t]
        for i in t13:
            if ms_intentos:
                t13_ms.append(min(abs(m - _ms(ventana[i])) for m in ms_intentos))
        intentos = [i for i, t in enumerate(ventana) if "mqtt: intento " in t]
        solapes = [a for a, b in zip(intentos, intentos[1:])
                   if not any(("(mqtt_down)" in u or "(mqtt_up)" in u) for u in ventana[a:b])]
        wifi = [t for t in ventana if "wifi: intento" in t or "-> CONECTANDO_WIFI" in t]
        del_nodo = _del_nodo(msgs, nodo, t_start)
        primero = next((m for m in del_nodo if m["payload"] != LWT), None)
        medida = next((m for m in del_nodo if m["topic"].rsplit("/", 1)[-1] in MEDIDAS), None)
        c.note("", "## Resultado", "",
               f"- T15: 1; T12: {t12}; T13: {len(t13)} (distancia máx. de T13 a su intento: {max(t13_ms, default=0)} ms)",
               *[f"- intervalo {k + 1}: {v} s (esperado {BACKOFF_S[k]} s ± 10 %)" for k, v in enumerate(intervalos)],
               f"- broker de vuelta: T11 {'sí' if vuelta else 'no'}; suscriptor resuscrito a "
               f"{(resus[0] - t_start) if resus else float('nan'):+.1f} s",
               f"- primer mensaje del nodo tras el arranque del broker: "
               f"{primero['topic'].replace(base, '<base>') if primero else '-'} a "
               f"{(primero['t'] - t_start) if primero else float('nan'):+.1f} s",
               f"- primera medida: {(medida['t'] - t_start) if medida else float('nan'):+.1f} s (límite 75 s)")
        assert len(intervalos) == len(BACKOFF_S), f"solo {len(intervalos)} intervalos medidos"
        for k, (v, e) in enumerate(zip(intervalos, BACKOFF_S)):
            assert v >= 0.9, f"intervalo {k + 1} en ráfaga: {v} s"
            assert abs(v - e) <= e * TOLERANCIA, f"intervalo {k + 1}: {v} s fuera de {e} s ± 10 %"
        assert t12 >= 10 and len(t13) >= 10, f"T12 {t12} / T13 {len(t13)}: menos de 10"
        assert len(t13_ms) == len(t13) and max(t13_ms, default=0) <= 1000, f"un T13 sin intento a ≤ 1 s: {t13_ms}"
        assert not solapes, "dos intentos MQTT sin un resultado entre ellos (T13)"
        assert not wifi, f"el Wi-Fi se tocó con el broker caído: {wifi[:2]}"
        _sin_reinicio(ent)
        assert vuelta, f"sin {T11} en 150 s tras arrancar el broker"
        if not resus or (primero and resus[0] > primero["t"]):
            pytest.skip("not done: el suscriptor no estaba resuscrito antes del primer mensaje del nodo")
        assert primero and primero["topic"] == f"{base}/status" and json.loads(primero["payload"]).get("estado") == "online", \
            f"el primer mensaje tras la reconexión no es status online (FR-MQTT-06): {primero}"
        assert medida and medida["t"] - t_start <= 75, "ninguna medida válida en ≤ 75 s tras volver el broker (FR-CON-04)"
        c.passed(f"10 intervalos MQTT dentro de ±10 % {intervalos}; sin Wi-Fi ni reinicio; status primero y "
                 f"medida a {medida['t'] - t_start:.1f} s")


def test_tc_con_09_wifi_loss_connecting_broker(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-09 · T14 — con el broker parado, el DUT se une al AP tras ≥ 4 fallos (último intervalo
    ≥ 8 s), queda en CONECTANDO_BROKER y se apaga el AP: con: CONECTANDO_BROKER -> CONECTANDO_WIFI
    (wifi_down), el siguiente «wifi: intento» en ≤ 2 s (backoff reiniciado en T08), sin más
    intentos MQTT y sin reiniciar."""
    tb = testbench
    with case(tb, "TC-CON-09", "Pérdida del Wi-Fi esperando al broker", run_dir, spec="TC-CON villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.step("Reset con el AP y el broker apagados; esperar «wifi: intento 5»")
        t0 = time.time()
        reg = Registro(tb, dut_slot, t0)
        tb.serial_reset(dut_slot)
        assert reg.esperar(r"wifi: intento 5\b", 60), "no llegó «wifi: intento 5» con el AP apagado"
        c.step("Levantar el AP (broker apagado); esperar T08 y dos intentos MQTT")
        banco.ap_on()
        t08 = reg.esperar(re.escape("con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)"), 60)
        assert t08, "sin T08 en 60 s con el AP arriba"
        assert reg.esperar(r"mqtt: intento 2\b", 30, desde_ts=t08["ts"]), "no hubo dos intentos MQTT"
        c.step("Apagar el AP; esperar T14 y observar 60 s")
        t_off = time.time()
        banco.ap_off()
        t14 = reg.esperar(re.escape("con: CONECTANDO_BROKER -> CONECTANDO_WIFI (wifi_down)"), 30, desde_ts=t_off)
        time.sleep(60)
        ent = _ultimo_arranque(reg)
        _guardar(c, ent, [], t0)
        textos = [e["text"] for e in ent]
        assert t14, "sin con: CONECTANDO_BROKER -> CONECTANDO_WIFI (wifi_down) en 30 s (T14)"
        i08 = next(i for i, t in enumerate(textos) if "-> CONECTANDO_BROKER (wifi_up)" in t)
        i14 = next(i for i, t in enumerate(textos) if "con: CONECTANDO_BROKER -> CONECTANDO_WIFI (wifi_down)" in t)
        # Intervalos de unión antes de T08 (del fallo al intento siguiente)
        antes = [_ms(t) for t in textos[:i08] if "wifi: intento " in t]
        previos = [round((b - a) / 1000, 1) for a, b in zip(antes, antes[1:])]
        sig = next((t for t in textos[i14 + 1:] if "wifi: intento " in t), None)
        dt = (_ms(sig) - _ms(textos[i14])) / 1000 if sig else None
        mqtt_tras = [t for t in textos[i14 + 1:] if "mqtt: intento" in t]
        c.note("", "## Resultado", "", f"- intentos de unión antes de T08: {len(antes)}; espacios entre intentos: {previos} s",
               f"- T14 a {(t14['ts'] - t_off):+.1f} s de apagar el AP; siguiente «wifi: intento» a "
               f"{dt if dt is not None else '-'} s de T14 (límite 2 s)",
               f"- intentos MQTT tras T14 en 60 s: {len(mqtt_tras)}")
        assert len(antes) >= 5, f"solo {len(antes)} intentos de unión antes de T08"
        assert max(previos[-2:]) >= 8, f"el último intervalo antes de T08 fue < 8 s: {previos}"
        assert dt is not None and dt <= 2.0, f"el siguiente «wifi: intento» llegó a {dt} s de T14 (backoff no reiniciado en T08)"
        assert not mqtt_tras, f"intentos MQTT tras T14: {mqtt_tras[:2]}"
        _sin_reinicio(ent)
        c.passed(f"T14; siguiente intento de unión a {dt} s; sin intentos MQTT ni reinicio")


def test_tc_con_10_wifi_loss_operativo(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-10 · T16, FR-CON-03, FR-MQTT-06 — en OPERATIVO se apaga el AP: con: OPERATIVO ->
    CONECTANDO_WIFI (wifi_down), siguiente «wifi: intento» en ≤ 2 s, sin reiniciar; al volver
    el AP, el primer mensaje del nodo es status online y una medida válida llega en ≤ 90 s."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-CON-10", "Pérdida del Wi-Fi en OPERATIVO", run_dir, spec="TC-CON villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            time.sleep(5)
            c.step("Apagar el AP 45 s")
            t_off = time.time()
            banco.ap_off()
            t16 = reg.esperar(re.escape("con: OPERATIVO -> CONECTANDO_WIFI (wifi_down)"), 30, desde_ts=t_off)
            time.sleep(max(0.0, t_off + 45 - time.time()))
            c.step("Levantar el AP; esperar T11 y la primera medida")
            t_on = time.time()
            banco.ap_on()
            vuelta = reg.esperar(re.escape(T11), 100, desde_ts=t_on)
            fin = time.time() + 30
            while time.time() < fin and not any(m["topic"].rsplit("/", 1)[-1] in MEDIDAS
                                                for m in _del_nodo(sub.mensajes(), nodo, t_on)):
                time.sleep(1)
            msgs = sub.mensajes()
        ent = _ultimo_arranque(reg)
        _guardar(c, ent, msgs, t0)
        textos = [e["text"] for e in ent]
        assert t16, "sin con: OPERATIVO -> CONECTANDO_WIFI (wifi_down) en 30 s (T16)"
        i16 = next(i for i, t in enumerate(textos) if "con: OPERATIVO -> CONECTANDO_WIFI (wifi_down)" in t)
        sig = next((t for t in textos[i16 + 1:] if "wifi: intento " in t), None)
        dt = (_ms(sig) - _ms(textos[i16])) / 1000 if sig else None
        t15 = [t for t in textos if "con: OPERATIVO -> CONECTANDO_BROKER" in t]
        del_nodo = _del_nodo(msgs, nodo, t_on)
        lwt = [m for m in del_nodo if m["payload"] == LWT]
        primero = next((m for m in del_nodo if m["payload"] != LWT), None)
        medida = next((m for m in del_nodo if m["topic"].rsplit("/", 1)[-1] in MEDIDAS), None)
        c.note("", "## Resultado", "",
               f"- T16 a {(t16['ts'] - t_off):+.1f} s de apagar el AP; siguiente «wifi: intento» a "
               f"{dt if dt is not None else '-'} s (límite 2 s)",
               f"- AP de vuelta: T11 {'sí' if vuelta else 'no'}; primer mensaje del nodo: "
               f"{primero['topic'].replace(base, '<base>') if primero else '-'}; Last Will de la sesión "
               f"anterior publicado por el broker: {len(lwt)}",
               f"- primera medida: {(medida['t'] - t_on) if medida else float('nan'):+.1f} s (límite 90 s)")
        assert not t15, f"la pérdida del Wi-Fi pasó por T15: {t15[:1]}"
        assert dt is not None and dt <= 2.0, f"el siguiente «wifi: intento» llegó a {dt} s de T16"
        _sin_reinicio(ent)
        assert vuelta, f"sin {T11} en 100 s tras levantar el AP"
        assert primero and primero["topic"] == f"{base}/status" and json.loads(primero["payload"]).get("estado") == "online", \
            f"el primer mensaje tras la reconexión no es status online (FR-MQTT-06): {primero}"
        assert medida and medida["t"] - t_on <= 90, "ninguna medida válida en ≤ 90 s tras volver el AP (FR-CON-03)"
        c.passed(f"T16; siguiente intento a {dt} s; status primero y medida a {medida['t'] - t_on:.1f} s del AP")


def test_tc_mqtt_04_last_will_on_power_cut(testbench, run_dir):
    """TC-MQTT-04 · FR-MQTT-05 — en cada corte de alimentación de esta sesión (JRN-01.7 y
    TC-CFG-02, hechos por el operador), el broker publica {"estado":"offline"} en status
    ≤ 100 s después del corte y queda retenido. No corta nada: lee lo que midieron."""
    from cortes import LWT_LIMITE_S, LWT_MEDIDOS
    tb = testbench
    with case(tb, "TC-MQTT-04", "Last Will tras un corte de alimentación", run_dir,
              spec="TC-MQTT villa-nodo-clima-piloto") as c:
        if not LWT_MEDIDOS:
            pytest.skip("not done: ningún corte de alimentación en esta sesión (JRN-01.7 o TC-CFG-02)")
        c.note("- corte = última muestra del slot presente antes de verlo ausente (cota por arriba del retraso)", "",
               "## Resultado", "",
               *[f"- {tid} corte {n}: Last Will {'—' if s is None else f'{s:.1f} s'}; retenido: {'sí' if ret else 'no'}"
                 for tid, n, s, ret in LWT_MEDIDOS])
        mal = [f"{tid} corte {n}: " + ("sin Last Will" if s is None else f"{s:.1f} s > {LWT_LIMITE_S} s" if s > LWT_LIMITE_S
                                       else "no quedó retenido")
               for tid, n, s, ret in LWT_MEDIDOS if s is None or s > LWT_LIMITE_S or not ret]
        assert not mal, "; ".join(mal)
        peor = max(s for _, _, s, _ in LWT_MEDIDOS)
        c.passed(f"{len(LWT_MEDIDOS)} cortes: Last Will retenido en ≤ {peor:.1f} s (límite {LWT_LIMITE_S} s)")
