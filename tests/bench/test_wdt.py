"""TC-WDT-01 — NFR-WDT-01 (fila bench) y aceptación 22.1-2: 24 h de estabilidad (FSD §20, §22.1;
Fase 2). Atómico y muy largo (≈ 24 h + preparación): graba la imagen de la CI, aprovisiona contra
un AP desechable nuevo, deja el nodo en OPERATIVO y lo observa 24 h con 3 cortes de broker de
5 min y 2 cortes de Wi-Fi (AP del banco apagado) de 5 min, todos por API: sin acción física ni
bench-serial-write. Deja el AP y el broker apagados al terminar.

Observación:
- NFR-WDT-01 (bench): uptime_s monótono en todos los status en vivo, reset sin cambio; ningún
  retroceso del reloj de esp_log en la ventana (H-78: un reinicio es eso, no el texto «boot:»;
  los bloques idénticos que el banco vuelve a entregar se descartan como relectura sin ocultar
  un reinicio real, consola.py) y ninguna línea con task_wdt.
- 22.1-2: Δlecturas = 1440 ± 2 en 24 h (en general, la duración en ciclos de 60 s ± 2);
  publicaciones por medida = ciclos en OPERATIVO ± 2 (ciclos en OPERATIVO = status en vivo:
  en OPERATIVO hay un status por ciclo, FR-MQTT-08; los ciclos sin OPERATIVO no publican);
  0 reinicios. Tras cada corte, un status en vivo en ≤ 150 s.
- Control positivo de la consola: med: en cada tramo de 10 min (si la captura se parase,
  «ningún boot:» no probaría nada) → si falla, not done.

Corrida de humo (no cuenta como resultado de TC-WDT-01): NODO_WDT_HUMO=1 → 15 min con un
corte de broker de 5 min; mismo código y mismas comprobaciones, escaladas a la duración."""
import json
import os
import re
import time

import pytest

from benchlib import case
from consola import quitar_relecturas, reinicios
from test_mqtt import MEDIDAS, _a_operativo, _nodo, _suscribir, configurado

CICLO_S = 60
CORTE_S = 300                  # 5 min por corte
VUELTA_S = 150                 # del servicio devuelto a un status en vivo (backoff de FR-CON-02 + ciclo)
LECTURA_CADA_S = 30            # el buffer serie del banco se lee por tramos (500 líneas por petición)
MED_MIN_POR_10MIN = 5
TOL_CICLOS = 2
BOOT = re.compile(r"\bboot: |rst:0x")

HUMO = os.environ.get("NODO_WDT_HUMO") == "1"
if HUMO:
    DURACION_S = 15 * 60
    CORTES = [(5 * 60, "broker")]
else:
    DURACION_S = 24 * 3600
    # 3 cortes de broker y 2 de Wi-Fi intercalados, separados ~4 h (s desde el inicio de la ventana)
    CORTES = [(2 * 3600, "broker"), (6 * 3600, "wifi"), (10 * 3600, "broker"),
              (14 * 3600, "wifi"), (18 * 3600, "broker")]


def _status_vivos(msgs, base, desde=0.0, hasta=float("inf")):
    out = []
    for m in msgs:
        if m["topic"] == f"{base}/status" and not m["retain"] and m["payload"] and desde <= m["t"] <= hasta:
            try:
                st = json.loads(m["payload"])
            except json.JSONDecodeError:
                continue
            if st.get("estado") == "online":
                out.append((m["t"], st))
    return out


def _huecos_med(ent, t_ini, t_fin):
    med = [e["ts"] for e in ent if "nodo: med: " in e.get("text", "") and t_ini <= e.get("ts", 0) <= t_fin]
    huecos, t = [], t_ini
    while t + 600 <= t_fin:
        n = sum(1 for x in med if t <= x < t + 600)
        if n < MED_MIN_POR_10MIN:
            huecos.append((round(t - t_ini), n))
        t += 600
    return len(med), huecos


def test_tc_wdt_01_24h_stability(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-WDT-01 · NFR-WDT-01 (bench) y aceptación 22.1-2 — 24 h con 3 cortes de broker y 2 de
    Wi-Fi de 5 min por API: uptime_s monótono y reset sin cambio en todos los status, 0 boot:,
    ningún task_wdt, Δlecturas = 1440 ± 2, publicaciones por medida = ciclos en OPERATIVO ± 2."""
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    nombre = "Estabilidad 24 h" if not HUMO else "Estabilidad (corrida de humo, 15 min)"
    with case(tb, "TC-WDT-01", nombre, run_dir, spec="TC-WDT villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        if HUMO:
            c.note("- **corrida de humo** (NODO_WDT_HUMO=1): no cuenta como resultado de TC-WDT-01", "")
        c.note(f"- ventana: {DURACION_S} s; cortes de {CORTE_S} s: "
               + ", ".join(f"{k} a t={t} s" for t, k in CORTES), "")
        banco.broker_on()
        cortes = []
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            fin = time.time() + 150
            while time.time() < fin and len(_status_vivos(sub.mensajes(), base, t0)) < 2:
                time.sleep(1)
            assert _status_vivos(sub.mensajes(), base, t0), "precondición: ningún status en vivo tras T11"
            c.step(f"Ventana de {DURACION_S // 3600} h {DURACION_S % 3600 // 60} min con {len(CORTES)} cortes")
            t_ini = time.time()
            t_fin = t_ini + DURACION_S
            pendientes = list(CORTES)
            while time.time() < t_fin:
                reg.leer()
                ahora = time.time()
                if pendientes and ahora - t_ini >= pendientes[0][0]:
                    _, tipo = pendientes.pop(0)
                    c.step(f"Corte de {tipo} {CORTE_S // 60} min (t={ahora - t_ini:.0f} s)")
                    t_c = time.time()
                    banco.broker_off() if tipo == "broker" else banco.ap_off()
                    while time.time() < t_c + CORTE_S:
                        reg.leer()
                        time.sleep(min(LECTURA_CADA_S, max(1.0, t_c + CORTE_S - time.time())))
                    t_v = time.time()
                    banco.broker_on() if tipo == "broker" else banco.ap_on()
                    cortes.append({"tipo": tipo, "t_corte": t_c, "t_vuelta": t_v})
                    continue
                time.sleep(min(LECTURA_CADA_S, max(1.0, t_fin - time.time())))
            time.sleep(5)
            reg.leer()
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])

        st = _status_vivos(msgs, base, t0)
        ventana = [x for x in st if t_ini - CICLO_S <= x[0] <= t_fin + 5]
        a, d = ventana[0][1], ventana[-1][1]
        uptimes = [s.get("uptime_s") for _, s in st]
        decrecientes = [(i, uptimes[i - 1], uptimes[i]) for i in range(1, len(uptimes))
                        if not (isinstance(uptimes[i], int) and isinstance(uptimes[i - 1], int) and uptimes[i] > uptimes[i - 1])]
        resets = sorted({s.get("reset") for _, s in st})
        limpias, relecturas = quitar_relecturas(ent)
        retrocesos = [limpias[k]["text"].strip() for k in reinicios(limpias)
                      if limpias[k].get("ts", 0) >= t_ini - CICLO_S]
        boots = [e["text"].strip() for e in limpias if e.get("ts", 0) >= t_ini - CICLO_S and BOOT.search(e.get("text", ""))]
        wdt = [e["text"].strip() for e in ent if "task_wdt" in e.get("text", "")]
        dt = ventana[-1][0] - ventana[0][0]
        ciclos = round(dt / CICLO_S)
        dlect = d["lecturas"] - a["lecturas"]
        derr = d["err_sensor"] - a["err_sensor"]
        en_operativo = len(ventana) - 1                      # status en vivo tras el primero = ciclos en OPERATIVO
        pubs = {k: len([m for m in msgs if m["topic"] == f"{base}/{k}" and not m["retain"] and m["payload"]
                        and ventana[0][0] + 1 < m["t"] <= ventana[-1][0] + 1]) for k in MEDIDAS}
        vueltas = []
        for k in cortes:
            nxt = next((t for t, _ in st if t > k["t_vuelta"]), None)
            vueltas.append((k["tipo"], round(k["t_corte"] - t_ini), None if nxt is None else round(nxt - k["t_vuelta"], 1)))
        n_med, huecos = _huecos_med(limpias, t_ini, t_fin)
        c.note("", "## Resultado", "",
               f"- status en vivo: {len(st)} ({len(ventana)} en la ventana); primero: uptime_s={a['uptime_s']}, "
               f"lecturas={a['lecturas']}, err_sensor={a['err_sensor']}, reset={a['reset']}; último: "
               f"uptime_s={d['uptime_s']}, lecturas={d['lecturas']}, err_sensor={d['err_sensor']}, reset={d['reset']}",
               f"- entre el primer y el último status: {dt:.0f} s = {ciclos} ciclos; Δlecturas = {dlect} "
               f"(esperado {ciclos} ± {TOL_CICLOS}); Δerr_sensor = {derr}",
               f"- ciclos en OPERATIVO (status en vivo): {en_operativo}; sin OPERATIVO: {dlect + derr - en_operativo}; "
               f"publicaciones por medida: {pubs}",
               *[f"- corte de {tipo} a t={tc} s: primer status en vivo a "
                 + (f"{v} s de devolverlo" if v is not None else "— (ninguno)") for tipo, tc, v in vueltas],
               f"- uptime_s no creciente: {decrecientes or 'ninguno'}; valores de reset: {resets}",
               f"- relecturas del banco descartadas: {len(relecturas)} bloque(s) de "
               f"{[n for _, n, _ in relecturas]} líneas; retrocesos del reloj de esp_log en la ventana: "
               f"{retrocesos or 'ninguno'}; líneas boot:/rst: en la ventana tras descartarlas: {len(boots)}; "
               f"líneas con task_wdt: {len(wdt)}",
               f"- control de la consola: {n_med} líneas med: en la ventana; tramos de 10 min con < "
               f"{MED_MIN_POR_10MIN}: {huecos or 'ninguno'}")
        assert not wdt, f"reinicio por watchdog: {wdt[:3]}"
        assert not retrocesos, f"reinicio en la ventana (retroceso del reloj de esp_log): {retrocesos[:3]}"
        assert not decrecientes, f"uptime_s no creciente: {decrecientes[:3]}"
        assert resets == [a["reset"]], f"reset cambió: {resets}"
        assert len(cortes) == len(CORTES), f"solo {len(cortes)} de {len(CORTES)} cortes hechos"
        assert all(v is not None and v <= VUELTA_S for _, _, v in vueltas), f"recuperación tras un corte > {VUELTA_S} s: {vueltas}"
        assert abs(dlect - ciclos) <= TOL_CICLOS, f"Δlecturas={dlect}, esperado {ciclos} ± {TOL_CICLOS}"
        malos = {k: n for k, n in pubs.items() if abs(n - en_operativo) > TOL_CICLOS}
        assert not malos, f"publicaciones por medida fuera de {en_operativo} ± {TOL_CICLOS}: {malos}"
        if huecos:
            pytest.skip(f"not done: la consola no capturó med: en algún tramo ({huecos}); «ningún boot:» no se puede afirmar")
        c.passed(f"{dt / 3600:.2f} h, {len(cortes)} cortes: 0 reinicios, uptime_s monótono, reset={a['reset']}, "
                 f"Δlecturas={dlect} ({ciclos} ± {TOL_CICLOS}), publicaciones {pubs} con {en_operativo} ciclos en OPERATIVO")
