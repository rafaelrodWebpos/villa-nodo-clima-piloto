"""Cortes de alimentación hechos por el operador y observados por MQTT (FSD 0.9.6; la consola
del banco no captura el arranque tras un corte, CR-TB-10). Lo usan JRN-01.7, TC-CFG-02 y
TC-MQTT-04.

La placa tiene un solo USB-C (C-HW-01): desenchufarlo del lado de la placa la deja sin
alimentación. Cada corte son dos avisos del banco (bench-operator-prompt): «desenchufa» y,
pasado el Last Will o 130 s, «vuelve a enchufar». El aviso corre en un hilo aparte y el
corte se detecta por la presencia USB del slot (get_slot → present), no por la respuesta del
aviso, que a veces no vuelve tras un remove/add USB (CR-TB-11).

Instantes (reloj de la laptop, el mismo que pone `t` a los mensajes MQTT):
- t_corte: la última muestra con el slot presente antes de verlo ausente (cota por arriba
  del retraso del Last Will: el corte real es posterior o igual).
- t_enchufe: la primera muestra con el slot presente otra vez.
"""
import json
import threading
import time

import pytest

from benchlib import suscriptor_mqtt

MEDIDAS = ("temperatura", "humedad", "punto_rocio")
LWT = '{"estado":"offline"}'
LWT_LIMITE_S = 100            # FR-MQTT-05
LWT_ESPERA_S = 130            # lo que se espera el Last Will antes de pedir reenchufar
MEDIDA_LIMITE_S = 30          # FR-CON-05, desde el encendido estimado
STATUS_ESPERA_S = 120         # del reenchufe al primer status en vivo
ESPERA_OPERADOR_S = 600       # lo que se espera a que el operador desenchufe o enchufe
MUESTREO_S = 0.5

AVISO_DESENCHUFAR = ("Corte {n} de {total} ({tid}): desenchufa el cable USB-C del lado de la PLACA "
                     "(el lado de la Raspberry Pi no se toca) y pulsa «Hecho». NO lo vuelvas a enchufar "
                     "todavía: en unos 2 minutos saldrá otro aviso.")
AVISO_ENCHUFAR = ("Corte {n} de {total} ({tid}): vuelve a enchufar el cable USB-C en la PLACA y "
                  "pulsa «Hecho».")

# Retrasos del Last Will medidos en esta sesión: [(tid, n, segundos o None, retenido)] para TC-MQTT-04
LWT_MEDIDOS = []


def filtros(nodo):
    """Cualquier sitio y zona (para ver un status con otros) y el Discovery del nodo."""
    return [f"+/+/{nodo}/#", f"homeassistant/sensor/{nodo}/#"]


def limpiar(nodo):
    base = f"sitio1/zona1/{nodo}"
    return [f"{base}/{m}" for m in ("status",) + MEDIDAS] + [f"homeassistant/sensor/{nodo}/{m}/config" for m in MEDIDAS]


def _presente(tb, slot):
    try:
        return bool(tb.get_slot(slot).get("present"))
    except Exception:      # un fallo de la API no es un cambio de presencia
        return None


def _aviso(tb, texto, c, etiqueta):
    """Lanza el aviso en un hilo; devuelve el hilo (no se espera su respuesta, CR-TB-11)."""
    res = {}

    def correr():
        try:
            res["ok"] = tb.human_interaction(texto, timeout=ESPERA_OPERADOR_S)
        except Exception as e:
            res["error"] = type(e).__name__
    h = threading.Thread(target=correr, daemon=True, name=etiqueta)
    h.res = res
    h.start()
    return h


def _esperar_presencia(tb, slot, quiero, timeout):
    """Muestrea el slot hasta ver present == quiero. Devuelve (t_ultima_contraria, t_vista) o None."""
    fin = time.time() + timeout
    t_contraria = time.time()
    while time.time() < fin:
        p = _presente(tb, slot)
        ahora = time.time()
        if p is quiero:
            return t_contraria, ahora
        if p is not None:
            t_contraria = ahora
        time.sleep(MUESTREO_S)
    return None


def en_vivo(msgs, desde, tema=None, nodo=None):
    """Mensajes en vivo (retain = 0) con payload desde `desde`."""
    out = [m for m in msgs if m["t"] >= desde and not m["retain"] and m["payload"]]
    if tema:
        out = [m for m in out if m["topic"] == tema]
    if nodo:
        out = [m for m in out if f"/{nodo}/" in m["topic"]]
    return out


def esperar_msg(sub, pred, timeout):
    fin = time.time() + timeout
    while True:
        hit = next((m for m in sub.mensajes() if pred(m)), None)
        if hit or time.time() > fin:
            return hit
        time.sleep(0.5)


def _status_retenido(tb, base):
    with suscriptor_mqtt(tb, f"{base}/status") as s2:
        time.sleep(3)
        ret = [m for m in s2.mensajes() if m["retain"] and m["payload"]]
    return ret[-1]["payload"] if ret else None


def corte(tb, slot, sub, nodo, tid, n, total, c):
    """Un corte completo. Devuelve un dict con lo observado; nunca afirma (decide el test).
    not done (skip) solo si el operador no desenchufa o no vuelve a enchufar a tiempo."""
    base = f"sitio1/zona1/{nodo}"
    r = {"n": n, "tid": tid}
    # 1) Desenchufar
    c.step(f"Corte {n}/{total}: aviso «desenchufa el USB-C de la placa»")
    h1 = _aviso(tb, AVISO_DESENCHUFAR.format(n=n, total=total, tid=tid), c, f"aviso-{tid}-{n}-a")
    vista = _esperar_presencia(tb, slot, False, ESPERA_OPERADOR_S)
    if not vista:
        pytest.skip(f"not done: el slot no quedó ausente en {ESPERA_OPERADOR_S} s (corte {n} sin hacer)")
    r["t_corte"], r["t_ausente"] = vista
    # 2) Last Will (FR-MQTT-05): en vivo, con el slot ausente
    lwt = esperar_msg(sub, lambda m: m["topic"] == f"{base}/status" and m["payload"] == LWT
                      and m["t"] >= r["t_corte"], LWT_ESPERA_S - (time.time() - r["t_corte"]))
    r["lwt_s"] = (lwt["t"] - r["t_corte"]) if lwt else None
    r["lwt_retenido"] = _status_retenido(tb, base) == LWT if lwt else False
    r["sigue_ausente"] = _presente(tb, slot) is False
    LWT_MEDIDOS.append((tid, n, r["lwt_s"], r["lwt_retenido"]))
    # 3) Volver a enchufar
    c.step(f"Corte {n}/{total}: aviso «vuelve a enchufar el USB-C en la placa»")
    h2 = _aviso(tb, AVISO_ENCHUFAR.format(n=n, total=total, tid=tid), c, f"aviso-{tid}-{n}-b")
    vista = _esperar_presencia(tb, slot, True, ESPERA_OPERADOR_S)
    if not vista:
        pytest.skip(f"not done: el slot no volvió a estar presente en {ESPERA_OPERADOR_S} s (corte {n})")
    r["t_enchufe"] = vista[1]
    # 4) Primer status en vivo tras el reenchufe (cualquier sitio/zona) y primera medida en vivo
    st = esperar_msg(sub, lambda m: m["topic"].endswith(f"/{nodo}/status") and not m["retain"]
                     and m["payload"] and m["payload"] != LWT and m["t"] >= r["t_ausente"], STATUS_ESPERA_S)
    r["status"] = st
    if st:
        try:
            cuerpo = json.loads(st["payload"])
        except json.JSONDecodeError:
            cuerpo = {}
        r["status_json"] = cuerpo
        up = cuerpo.get("uptime_s")
        r["encendido"] = st["t"] - up - 2 if isinstance(up, int) and not isinstance(up, bool) else None
        med = esperar_msg(sub, lambda m: m["topic"].rsplit("/", 1)[-1] in MEDIDAS and m["topic"].count("/") == 3
                          and f"/{nodo}/" in m["topic"] and not m["retain"] and m["payload"] and m["t"] >= st["t"],
                          MEDIDA_LIMITE_S + 10)
        r["medida"] = med
        r["medida_s"] = (med["t"] - r["encendido"]) if med and r["encendido"] is not None else None
    # 5) Nunca el portal: escaneo con el AP del banco arriba (FR-013 del banco)
    c.step(f"Corte {n}/{total}: escaneo Wi-Fi (no debe verse ningún clima-*)")
    try:
        nets = tb.scan().get("networks") or []
        r["clima_ap"] = sorted({x.get("ssid", "") for x in nets if str(x.get("ssid", "")).startswith("clima-")})
        r["escaneo_ok"] = True
    except Exception as e:
        r["clima_ap"], r["escaneo_ok"] = [], False
        r["escaneo_error"] = type(e).__name__
    r["avisos"] = [h1.res.get("ok", h1.res.get("error", "sin respuesta")), h2.res.get("ok", h2.res.get("error", "sin respuesta"))]
    return r


def resumen(r):
    st = r.get("status_json") or {}
    tema = r["status"]["topic"] if r.get("status") else "—"
    f = lambda v: "—" if v is None else f"{v:.1f} s"
    return (f"- corte {r['n']}: ausente {r['t_ausente'] - r['t_corte']:.1f} s tras la última muestra presente; "
            f"Last Will {f(r.get('lwt_s'))} (retenido: {'sí' if r.get('lwt_retenido') else 'no'}); "
            f"reenchufe a {r['t_enchufe'] - r['t_corte']:.0f} s; primer status `{tema}` reset={st.get('reset')} "
            f"uptime_s={st.get('uptime_s')} a {f(r['status']['t'] - r['t_enchufe'] if r.get('status') else None)} del reenchufe; "
            f"primera medida a {f(r.get('medida_s'))} del encendido estimado; clima-* en el escaneo: "
            f"{r['clima_ap'] or 'ninguno'}{'' if r.get('escaneo_ok') else ' (escaneo falló: ' + r.get('escaneo_error', '?') + ')'}; "
            f"avisos: {r['avisos']}")


def errores(r, nodo, cfg_y_portal=True, arranque=True, lwt=False):
    """Lista de incumplimientos de un corte."""
    out = []
    base = f"sitio1/zona1/{nodo}"
    st = r.get("status")
    if not st:
        return [f"corte {r['n']}: ningún status en vivo en {STATUS_ESPERA_S} s tras reenchufar"]
    cuerpo = r.get("status_json") or {}
    if cfg_y_portal:
        if st["topic"] != f"{base}/status":
            out.append(f"corte {r['n']}: status bajo {st['topic']}, no {base}/status (FR-CFG-01)")
        if r.get("clima_ap"):
            out.append(f"corte {r['n']}: AP del portal en el escaneo {r['clima_ap']}")
        if not r.get("escaneo_ok"):
            out.append(f"corte {r['n']}: el escaneo no se pudo hacer ({r.get('escaneo_error')})")
    if cuerpo.get("estado") != "online":
        out.append(f"corte {r['n']}: el primer status no es online: {st['payload']}")
    if cuerpo.get("reset") != "poweron":
        out.append(f"corte {r['n']}: reset={cuerpo.get('reset')}, no poweron")
    if arranque:
        if r.get("medida_s") is None:
            out.append(f"corte {r['n']}: sin medida en vivo tras el status (o sin uptime_s)")
        elif r["medida_s"] > MEDIDA_LIMITE_S:
            out.append(f"corte {r['n']}: primera medida a {r['medida_s']:.1f} s del encendido estimado (> {MEDIDA_LIMITE_S} s, FR-CON-05)")
    if lwt:
        if r.get("lwt_s") is None:
            out.append(f"corte {r['n']}: sin Last Will en {LWT_ESPERA_S} s")
        elif r["lwt_s"] > LWT_LIMITE_S:
            out.append(f"corte {r['n']}: Last Will a {r['lwt_s']:.1f} s (> {LWT_LIMITE_S} s)")
    return out


def guardar_mqtt(c, sub, t0):
    c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                        for m in sub.mensajes()])


def preparar(tb, slot, banco, sub, c):
    """Broker ya arriba y suscriptor conectado: reset, AP arriba, T11 y una medida en vivo.
    Devuelve (t0, Registro)."""
    from test_mqtt import _a_operativo
    t0, reg = _a_operativo(tb, slot, banco, c)
    med = esperar_msg(sub, lambda m: m["topic"].rsplit("/", 1)[-1] in MEDIDAS and not m["retain"]
                      and m["payload"] and m["t"] >= t0, 90)
    assert med, "precondición: ninguna medida en vivo tras T11"
    time.sleep(5)
    return t0, reg
