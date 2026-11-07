"""TC-CON-11 y TC-CON-12 — FR-CON-01: ningún reinicio por conectividad (FSD §6.6; Fase 2).
Caso A: AP del banco apagado 60 min. Caso B: broker parado 60 min con el Wi-Fi arriba.
Atómicos y largos (≈ 65 min cada uno): graban la imagen de la CI, aprovisionan contra un AP
desechable nuevo y dejan el AP y el broker apagados al terminar.

Observación (contrato de FR-CON-01): en el primer status tras la recuperación, uptime_s ≥
duración del corte y el mismo reset que antes; ninguna línea boot: en la consola durante la
ventana (corte + 120 s); ningún SSID clima-* en los escaneos de la ventana. Control positivo
de la consola: las líneas med: siguen llegando durante toda la ventana (si la captura se
parase, «ningún boot:» no probaría nada).

El banco no escanea con su AP encendido (CR-TB-14): en el caso A se escanea durante el corte
(AP apagado); en el caso B, como en H-63, al final se apaga el AP un momento para escanear y
se vuelve a encender."""
import json
import re
import time

import pytest

from benchlib import case
from test_mqtt import MEDIDAS, _a_operativo, _nodo, _suscribir, configurado

CORTE_S = 3600                 # 60 min (FR-CON-01)
TRAS_S = 120                   # la ventana es corte + 120 s
ESCANEO_CADA_S = 600           # caso A: un escaneo cada 10 min con el AP apagado
LECTURA_CADA_S = 60            # el buffer serie del banco se lee por tramos
MED_MIN_POR_10MIN = 5          # control positivo: med: cada 60 s → ≥ 5 en cada tramo de 10 min
BOOT = re.compile(r"\bboot: |rst:0x")


def _status_vivos(msgs, base, desde=0.0):
    out = []
    for m in msgs:
        if m["topic"] == f"{base}/status" and not m["retain"] and m["payload"] and m["t"] >= desde:
            try:
                st = json.loads(m["payload"])
            except json.JSONDecodeError:
                continue
            if st.get("estado") == "online":
                out.append((m, st))
    return out


def _escanear(tb, intentos=3):
    fallos = []
    for _ in range(intentos):
        try:
            nets = tb.scan().get("networks") or []
            return sorted({str(x.get("ssid", "")) for x in nets if str(x.get("ssid", "")).startswith("clima-")}), fallos
        except Exception as e:
            fallos.append(type(e).__name__)
    return None, fallos


def _huecos_med(ent, t_ini, t_fin):
    """Tramos de 10 min de la ventana con menos de MED_MIN_POR_10MIN líneas med:."""
    med = [e["ts"] for e in ent if "nodo: med: " in e.get("text", "") and t_ini <= e.get("ts", 0) <= t_fin]
    huecos, t = [], t_ini
    while t + 600 <= t_fin:
        n = sum(1 for x in med if t <= x < t + 600)
        if n < MED_MIN_POR_10MIN:
            huecos.append((round(t - t_ini), n))
        t += 600
    return len(med), huecos


def _corte_largo(tb, dut_slot, dut_mac, firmware, run_dir, tmp_path, tid, nombre, caso):
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, tid, nombre, run_dir, spec="TC-CON villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        escaneos = []
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            fin = time.time() + 90
            while time.time() < fin and not any(m["topic"].rsplit("/", 1)[-1] in MEDIDAS and not m["retain"]
                                                and m["t"] >= t0 for m in sub.mensajes()):
                time.sleep(1)
            time.sleep(5)
            antes = _status_vivos(sub.mensajes(), base, t0)
            assert antes, "precondición: ningún status en vivo tras T11"
            reset_antes, uptime_antes = antes[-1][1].get("reset"), antes[-1][1].get("uptime_s")
            c.step(f"Corte de 60 min: {'AP del banco apagado' if caso == 'A' else 'broker parado (Wi-Fi arriba)'}")
            t_corte = time.time()
            if caso == "A":
                banco.ap_off()
            else:
                banco.broker_off()
            prox_escaneo = t_corte + 60
            while time.time() < t_corte + CORTE_S:
                reg.leer()
                if caso == "A" and time.time() >= prox_escaneo:
                    vistos, fallos = _escanear(tb)
                    escaneos.append((round(time.time() - t_corte), vistos, fallos))
                    prox_escaneo += ESCANEO_CADA_S
                time.sleep(min(LECTURA_CADA_S, max(1.0, t_corte + CORTE_S - time.time())))
            c.step("Fin del corte: devolver " + ("el AP" if caso == "A" else "el broker") + "; esperar el primer status")
            t_vuelta = time.time()
            if caso == "A":
                if not escaneos or escaneos[-1][0] < CORTE_S - 120:      # un último escaneo justo antes de volver
                    vistos, fallos = _escanear(tb)
                    escaneos.append((round(time.time() - t_corte), vistos, fallos))
                    t_vuelta = time.time()
                banco.ap_on()
            else:
                banco.broker_on()
            fin = t_vuelta + TRAS_S
            despues = []
            while time.time() < fin:
                reg.leer()
                despues = despues or _status_vivos(sub.mensajes(), base, t_vuelta)
                time.sleep(2)
            reg.leer()
            if caso == "B":
                c.step("Escaneo con el AP del banco apagado un momento (CR-TB-14, como H-63)")
                banco.ap_off()
                try:
                    time.sleep(3)
                    vistos, fallos = _escanear(tb)
                    escaneos.append((round(time.time() - t_corte), vistos, fallos))
                finally:
                    banco.ap_on()
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])
        t_fin_ventana = t_vuelta + TRAS_S
        boots = [e["text"] for e in ent if t_corte <= e.get("ts", 0) <= t_fin_ventana + 5 and BOOT.search(e.get("text", ""))]
        n_med, huecos = _huecos_med(ent, t_corte, t_corte + CORTE_S)
        primero = despues[0][1] if despues else None
        c.note("", "## Resultado", "",
               f"- antes del corte: reset={reset_antes}, uptime_s={uptime_antes}",
               f"- primer status tras la vuelta: " + (f"a {despues[0][0]['t'] - t_vuelta:+.1f} s, reset={primero.get('reset')}, "
                                                      f"uptime_s={primero.get('uptime_s')}" if primero else "ninguno en 120 s"),
               f"- líneas boot:/rst: en la ventana: {len(boots)}",
               f"- control de la consola: {n_med} líneas med: durante el corte; tramos de 10 min con < "
               f"{MED_MIN_POR_10MIN}: {huecos or 'ninguno'}",
               *[f"- escaneo a t={t} s: " + ("sin hacer (" + ", ".join(f) + ")" if v is None else (str(v) if v else "ningún clima-*"))
                 + (f" (fallos previos: {', '.join(f)})" if v is not None and f else "") for t, v, f in escaneos])
        assert not boots, f"reinicio en la ventana: {boots[:3]}"
        assert primero, f"ningún status en vivo en {TRAS_S} s tras devolver {'el AP' if caso == 'A' else 'el broker'}"
        assert isinstance(primero.get("uptime_s"), int) and primero["uptime_s"] >= CORTE_S, \
            f"uptime_s={primero.get('uptime_s')} < {CORTE_S}: el nodo se reinició"
        assert primero.get("reset") == reset_antes, f"reset cambió: {reset_antes} → {primero.get('reset')}"
        assert all(not v for _, v, _ in escaneos if v is not None), f"AP del portal en un escaneo: {escaneos}"
        if huecos:
            pytest.skip(f"not done: la consola no capturó med: en algún tramo ({huecos}); «ningún boot:» no se puede afirmar")
        if not escaneos or any(v is None for _, v, _ in escaneos):
            pytest.skip(f"not done: algún escaneo sin hacer ({escaneos})")
        c.passed(f"corte de 60 min sin reinicio: uptime_s={primero['uptime_s']}, reset={primero['reset']}, "
                 f"0 boot:, {len(escaneos)} escaneos sin clima-*")


def test_tc_con_11_ap_off_60_min(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-11 · FR-CON-01 caso A — AP del banco apagado 60 min: ningún reinicio, nunca el portal."""
    _corte_largo(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path, "TC-CON-11", "AP apagado 60 min", "A")


def test_tc_con_12_broker_off_60_min(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-12 · FR-CON-01 caso B — broker parado 60 min con el Wi-Fi arriba: ningún reinicio."""
    _corte_largo(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path, "TC-CON-12", "Broker parado 60 min", "B")
