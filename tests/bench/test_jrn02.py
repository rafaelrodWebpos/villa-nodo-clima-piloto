"""Fase 3 — OTA contra la pre-release ota-test-2 (la 1 llevaba el adaptador anterior a los arreglos de redirección) (bench⁺, imagen de banco, FR-OTA-13). Atómicos:
cada test graba la imagen A de la CI, aprovisiona y deja el nodo en OPERATIVO con salida a Internet.

JRN-02.1 · T17, T19, FR-OTA-02, FR-OTA-06, FR-CFG-01 (OTA), FR-OTA-05 (misma versión):
  A → B1 → (B1 otra vez: rechazado:misma_version) → B2.
TC-OTA-10 · FR-OTA-05: imagen para esp32 e imagen truncada → error:imagen, sin cambio de slot.
TC-OTA-11 · FR-OTA-08, T22, FR-MQTT-09 (fila 2): AP apagado 30 s a mitad de descarga → error:red,
  sigue A, y un reset arranca A en su misma partición.
TC-OTA-12 · FR-OTA-10, T21: segundo comando durante la descarga → rechazado:ocupado → ok → fw = B1."""
import json
import re
import time

import pytest

from benchlib import case
from test_mqtt import _a_operativo, _nodo, _suscribir, configurado
from test_ota import _publicar, _status

REL = "https://github.com/rafaelrodWebpos/villa-nodo-clima-piloto/releases/download/ota-test-2/"
B1, B2 = "0.0.1-ota-test.2.1", "0.0.1-ota-test.2.2"
BOOT = re.compile(r"nodo: boot: \S+ fw=(\S+) reset=(\w+) part=(\w+) img=(\w+)")


def _vivos(sub, base, desde):
    return [(t, s) for t, s in _status(sub.mensajes(), base, desde) if s.get("estado") == "online"]


def _ota(tb, base, asset):
    return _publicar(tb, f"{base}/cmd/ota", json.dumps({"url": REL + asset}).encode())


def _esperar(sub, base, desde, cond, plazo):
    fin = time.time() + plazo
    while time.time() < fin:
        hit = next(((t, s) for t, s in _vivos(sub, base, desde) if cond(s)), None)
        if hit:
            return hit
        time.sleep(1)
    return None


def _a_version(c, tb, sub, reg, base, asset, version, vigilar_s=0):
    """OTA completa a `version`: en_curso ≤ 2 s, ok, boot de la nueva pendiente, T11 y E9,
    fw nuevo ≤ 120 s desde el status con ok; sin rollback durante vigilar_s."""
    t = _ota(tb, base, asset)
    en = _esperar(sub, base, t, lambda s: s.get("ota") == "en_curso", 10)
    ok = _esperar(sub, base, t, lambda s: s.get("ota") == "ok", 240)
    assert en and en[0] - t <= 2.0, f"{version}: en_curso no llegó en ≤ 2 s"
    assert ok, f"{version}: sin ota = ok"
    nuevo = _esperar(sub, base, ok[0], lambda s: s.get("fw") == version, 180)
    assert nuevo, f"{version}: ningún status con fw = {version}"
    dt = nuevo[0] - ok[0]
    boot = reg.esperar(re.escape(f"fw={version}"), 30, desde_ts=t)
    assert boot and BOOT.search(boot["text"]).group(4) == "pendiente", f"{version}: boot sin img=pendiente"
    assert reg.esperar(re.escape("ota: imagen validada"), 30, desde_ts=boot["ts"]), f"{version}: sin E9"
    if vigilar_s:
        time.sleep(vigilar_s)
        st = [s for _, s in _vivos(sub, base, nuevo[0])]
        malos = [s for s in st if s.get("fw") != version]
        ups = [s.get("uptime_s") for s in st]
        assert not malos and all(b > a for a, b in zip(ups, ups[1:])), f"{version}: rollback o reinicio tras validar"
    c.note(f"- {version}: en_curso a {en[0] - t:.2f} s; ok; fw = {version} a {dt:.1f} s del ok (≤ 120 s); "
           f"boot img=pendiente, E9" + (f"; {vigilar_s} s sin rollback" if vigilar_s else ""))
    assert dt <= 120, f"{version}: fw nuevo a {dt:.1f} s del ok"
    return boot


def test_jrn_02_1_ota_to_b1_and_b2(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """JRN-02.1 — A → B1 → B1 (misma_version) → B2, por cmd/ota contra ota-test-1."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    with case(tb, "JRN-02.1", "OTA a B1 y a B2", run_dir, spec="JRN-02 villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            time.sleep(3)
            c.step("OTA A → B1, y 310 s de vigilancia (FR-OTA-06)")
            _a_version(c, tb, sub, reg, base, "firmware_b1.bin", B1, vigilar_s=310)
            c.step("B1 otra vez: rechazado:misma_version (FR-OTA-05)")
            t = _ota(tb, base, "firmware_b1.bin")
            mv = _esperar(sub, base, t, lambda s: s.get("ota") == "rechazado:misma_version", 120)
            assert mv, "sin rechazado:misma_version"
            c.note(f"- B1 sobre B1: rechazado:misma_version a {mv[0] - t:.1f} s")
            c.step("OTA B1 → B2 (FR-OTA-02, segunda versión)")
            _a_version(c, tb, sub, reg, base, "firmware_b2.bin", B2)
            txt = [e.get("text", "") for e in reg.leer()]
        c.save_log("serie", txt)
        assert not any("-> PORTAL" in t for t in txt[1:]), "abrió el portal tras una OTA (FR-CFG-01)"
        c.passed(f"A → {B1} → misma_version → {B2}; mismos tópicos, sin portal")


def test_tc_ota_10_bad_images(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-10 · FR-OTA-05 — imagen para esp32 y truncada: error:imagen, sin cambio de slot."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    with case(tb, "TC-OTA-10", "Imágenes inválidas (error:imagen)", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            t0 = time.time()
            for asset in ("firmware_esp32.bin", "firmware_truncada.bin"):
                c.step(f"Comando con {asset}")
                t = _ota(tb, base, asset)
                r = _esperar(sub, base, t, lambda s: s.get("ota") == "error:imagen", 180)
                c.note(f"- {asset}: " + ("error:imagen a " + f"{r[0] - t:.1f} s" if r else "sin error:imagen"))
                assert r, f"{asset}: sin error:imagen"
                time.sleep(3)
            txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t0]
        c.save_log("serie", txt)
        assert not any(BOOT.search(t) for t in txt), "reinició o cambió de slot"
        c.passed("esp32 y truncada: error:imagen, sin reinicio")


def test_tc_ota_11_ap_lost_during_download(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-11 · FR-OTA-08, T22, FR-MQTT-09 — AP apagado 30 s a mitad de descarga."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    with case(tb, "TC-OTA-11", "Wi-Fi perdido durante la descarga", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            boot_a = reg.esperar(BOOT.pattern, 5)
            part_a = BOOT.search(boot_a["text"]).group(3) if boot_a else None
            t = _ota(tb, base, "firmware_b1.bin")
            p = reg.esperar(r"nodo: ota: [3-9]0 %", 120, desde_ts=t)
            assert p, "la descarga no llegó al 30 %"
            c.step(f"Apagar el AP 30 s a mitad de descarga ({p['text'].strip()[-6:]})")
            banco.ap_off()
            time.sleep(30)
            t_on = time.time()
            banco.ap_on(internet=True)
            primero = _esperar(sub, base, t_on, lambda s: True, 150)
            assert primero, "sin status tras volver el AP"
            c.step("Reset por la línea del banco: debe arrancar A en su partición")
            t_r = time.time()
            tb.serial_reset(dut_slot)
            boot = reg.esperar(BOOT.pattern, 60, desde_ts=t_r)
            txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t]
        c.save_log("serie", txt)
        s = primero[1]
        c.note(f"- primer status tras volver el AP: ota={s.get('ota')} fw={s.get('fw')}",
               f"- tras el reset: {BOOT.search(boot['text']).group(0) if boot else '—'} (A en {part_a})")
        assert any("OTA_DESCARGA -> CONECTANDO_WIFI (wifi_down)" in x for x in txt), "sin T22"
        assert any("ota: estado error:red" in x for x in txt), "sin E7 error:red"
        assert s.get("ota") == "error:red" and s.get("fw") == firmware["version"], f"primer status: {s}"
        assert boot and BOOT.search(boot["text"]).group(1) == firmware["version"], "tras el reset no arrancó A"
        assert BOOT.search(boot["text"]).group(3) == part_a, "A arrancó en otra partición"
        c.passed("T22, error:red en el primer status, A sigue y arranca en su partición")


def test_tc_ota_12_busy_during_download(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-12 · FR-OTA-10, T21 — en_curso → rechazado:ocupado → ok → fw = B1."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    with case(tb, "TC-OTA-12", "Comando durante la descarga (ocupado)", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            t = _ota(tb, base, "firmware_b1.bin")
            assert reg.esperar(r"nodo: ota: \d+ %", 60, desde_ts=t), "la descarga no empezó"
            _ota(tb, base, "firmware_b2.bin")
            fw = _esperar(sub, base, t, lambda s: s.get("fw") == B1, 300)
            otas = [s.get("ota") for _, s in _vivos(sub, base, t)]
        seq = [o for i, o in enumerate(otas) if i == 0 or o != otas[i - 1]]
        c.note(f"- ota en status: {seq}; fw = B1: {'sí' if fw else 'no'}")
        assert seq[:3] == ["en_curso", "rechazado:ocupado", "ok"], f"secuencia: {seq}"
        assert fw, "fw no pasó a B1"
        c.passed("en_curso → rechazado:ocupado → ok y fw = B1")


def test_jrn_02_2_rollback_when_new_image_never_operative(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """JRN-02.2 · FR-OTA-07, T23 — imagen sin MQTT: boot B pendiente, «ota: rollback» ≤ 300 s,
    boot A, primer status fw = A y 15 min sin reinicio."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    a = firmware["version"]
    with case(tb, "JRN-02.2", "Rollback de una imagen que no llega a OPERATIVO", run_dir, spec="JRN-02 villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            t = _ota(tb, base, "firmware_sin_mqtt.bin")
            assert _esperar(sub, base, t, lambda s: s.get("ota") == "ok", 240), "sin ota = ok"
            b = reg.esperar(r"fw=0\.0\.1-ota-test\.2\.3 .*img=pendiente", 60, desde_ts=t)
            assert b, "sin boot de B con img=pendiente"
            c.step("Esperar el rollback (T23, ≤ 300 s desde el boot de B)")
            rb = reg.esperar(re.escape("ota: rollback"), 330, desde_ts=b["ts"])
            assert rb, "sin «ota: rollback» en 330 s"
            ba = reg.esperar(re.escape(f"fw={a} "), 60, desde_ts=rb["ts"])
            assert ba, "no volvió a arrancar A"
            st_a = _esperar(sub, base, ba["ts"], lambda s: True, 150)
            assert st_a and st_a[1].get("fw") == a, f"primer status tras la vuelta: {st_a}"
            c.step("15 min de vigilancia tras el primer status de A")
            time.sleep(900)
            st = [s for _, s in _vivos(sub, base, st_a[0])]
            txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t]
        c.save_log("serie", txt)
        dt = rb["ts"] - b["ts"]
        ups = [s.get("uptime_s") for s in st]
        boots_despues = [x for x in txt[txt.index(ba["text"]) + 1:] if BOOT.search(x)] if ba["text"] in txt else []
        c.note(f"- boot de B (pendiente) → «ota: rollback»: {dt:.1f} s (≤ 300 s)",
               f"- de vuelta: {BOOT.search(ba['text']).group(0) if BOOT.search(ba['text']) else ba['text']}",
               f"- 15 min: {len(st)} status, fw {sorted({s.get('fw') for s in st})}, uptime_s monótono: "
               f"{all(y > x for x, y in zip(ups, ups[1:]))}; boot: posteriores {len(boots_despues)}")
        assert dt <= 305, f"rollback a {dt:.1f} s"
        assert len(st) >= 10 and all(s.get("fw") == a for s in st), "status sin fw = A"
        assert all(y > x for x, y in zip(ups, ups[1:])) and not boots_despues, "reinicio tras la vuelta"
        c.passed(f"rollback a {dt:.0f} s del boot de B; A estable 15 min")


MED_MS = re.compile(r"\s*I \((\d+)\) nodo: med: ")


def test_nfr_ota_01_measurement_period_during_download(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """NFR-OTA-01 — tres OTAs alternas con una medida dentro de OTA_DESCARGA: intervalos en [55, 65] s."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    with case(tb, "TC-OTA-13", "Periodo de medición durante la descarga", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        intervalos = []
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            for asset, ver in (("firmware_b1.bin", B1), ("firmware_b2.bin", B2), ("firmware_b1.bin", B1)):
                m = reg.esperar(MED_MS.pattern, 90, desde_ts=time.time())     # una medida reciente de esta imagen
                assert m, "sin med:"
                time.sleep(max(0.0, m["ts"] + 50 - time.time()))              # ~10 s antes de la siguiente
                t = _ota(tb, base, asset)
                ok = reg.esperar(r"con: OTA_DESCARGA -> ARRANQUE \(ota_ok\)", 240, desde_ts=t)
                assert ok, f"{ver}: la OTA no terminó"
                txt = [e.get("text", "") for e in reg.leer() if m["ts"] - 1 <= e.get("ts", 0) <= ok["ts"] + 1]
                ms = [int(MED_MS.match(x).group(1)) for x in txt if MED_MS.match(x)]
                ini = next(x for x in txt if "-> OTA_DESCARGA (cmd_ota)" in x)
                t_ini = int(re.match(r"\s*I \((\d+)\)", ini).group(1))
                dentro = [x for x in ms if x >= t_ini]
                if len(ms) >= 2 and dentro:
                    intervalos.append(round((dentro[0] - ms[ms.index(dentro[0]) - 1]) / 1000, 2))
                assert _esperar(sub, base, t, lambda s, v=ver: s.get("fw") == v, 180), f"no arrancó {ver}"
                time.sleep(5)
        c.note(f"- intervalos con una medida dentro de OTA_DESCARGA (s): {intervalos}")
        assert len(intervalos) >= 3, f"solo {len(intervalos)} intervalos con una medida en la descarga"
        assert all(55 <= x <= 65 for x in intervalos), f"fuera de [55, 65] s: {intervalos}"
        c.passed(f"{len(intervalos)} intervalos en [55, 65] s: {intervalos}")


OTA_PCT = re.compile(r"nodo: ota: (\d+) %")
AVISO_LISTO = ("TC-OTA-15: ponte junto a la placa. Al pulsar «Hecho» se manda la OTA; unos 10 s después sale el "
               "aviso de desenchufar el USB-C de la PLACA: hazlo en cuanto salga (quedan ~20 s de descarga).")


def test_tc_ota_15_power_cut_during_download(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-15 · T17 («no debe ocurrir»), H-89 — corte del USB-C de la placa durante la descarga:
    arranca la imagen anterior (reset=poweron), sin rollback, y el primer status lleva fw = A."""
    import cortes
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    a = firmware["version"]
    with case(tb, "TC-OTA-15", "Corte de alimentación durante la descarga OTA", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            c.step("Aviso previo: el operador se pone junto a la placa")
            if not tb.human_interaction(AVISO_LISTO, timeout=cortes.ESPERA_OPERADOR_S):
                pytest.skip("not done: el operador no confirmó el aviso previo")
            t = _ota(tb, base, "firmware_b1.bin")
            # el aviso sale con la escritura ya empezada (≥ 10 %): queda ~20 s para desenchufar
            # (2026-11-15: con el aviso enseguida, el corte cayó antes del primer «ota: 0 %»)
            if not reg.esperar(r"nodo: ota: [1-9]0 %", 60, desde_ts=t):
                pytest.skip("not done: la descarga no llegó al 10 % en 60 s")
            r = cortes.corte(tb, dut_slot, sub, nodo, "TC-OTA-15", 1, 1, c, banco)
            antes = [e.get("text", "") for e in reg.leer() if t - 1 <= e.get("ts", 0) <= r["t_ausente"]]
            pcts = [int(m.group(1)) for x in antes if (m := OTA_PCT.search(x))]
            en_descarga = any("-> OTA_DESCARGA (cmd_ota)" in x for x in antes)
            termino = any("OTA_DESCARGA -> ARRANQUE" in x for x in antes) or (pcts and pcts[-1] >= 100)
            if not en_descarga or termino or not pcts:
                pytest.skip(f"not done: el corte no cayó dentro de la descarga (último ota: {pcts[-1:] or '—'} %); repetir")
            st0 = r.get("status_json") or {}
            c.step("Vigilar 330 s (T23 vence a los 300 s) que no haya rollback ni reinicio")
            t_st = r["status"]["t"] if r.get("status") else time.time()
            time.sleep(330)
            st = [s for _, s in _vivos(sub, base, t_st)]
        c.save_log("serie-antes-del-corte", antes)
        ups = [s.get("uptime_s") for s in st]
        c.note(cortes.resumen(r),
               f"- último «ota: n %» antes del corte: {pcts[-1] if pcts else '—'} %",
               f"- primer status tras el reenchufe: fw={st0.get('fw')} reset={st0.get('reset')} ota={st0.get('ota')}",
               f"- 330 s después: {len(st)} status, fw {sorted({s.get('fw') for s in st})}, uptime_s monótono: "
               f"{all(y > x for x, y in zip(ups, ups[1:]))}")
        assert st0.get("fw") == a, f"primer status con fw={st0.get('fw')} (esperado {a})"
        assert st0.get("reset") == "poweron", f"reset={st0.get('reset')}"
        assert len(st) >= 4 and all(s.get("fw") == a for s in st), "status sin fw = A tras el corte"
        assert all(y > x for x, y in zip(ups, ups[1:])), "reinicio (rollback) tras el corte"
        c.passed(f"corte al {pcts[-1]} % de la descarga; arrancó A ({a}) con reset=poweron y siguió 330 s sin rollback")


def test_tc_ota_17_abort_slow_download_then_new_command(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-OTA-17 · FR-OTA-08, T22, T20 — revisión 2026-11-18 (A3-03, B-1): una descarga lenta
    (sin salida a Internet) se aborta por T22; un cmd_ota nuevo mientras la tarea vieja sigue
    viva da error:red; la imagen abortada no queda arrancable (un reset arranca A en su
    partición) y el cmd_ota siguiente termina en fw = B2, sin que B1 arranque nunca."""
    tb = testbench
    base = f"sitio1/zona1/{_nodo(dut_mac)}"
    a = firmware["version"]
    with case(tb, "TC-OTA-17", "Aborto de una OTA lenta y cmd_ota nuevo", run_dir, spec="TC-OTA villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, _nodo(dut_mac)) as sub:
            _, reg = _a_operativo(tb, dut_slot, banco, c, internet=True)
            boot_a = reg.esperar(BOOT.pattern, 5)
            part_a = BOOT.search(boot_a["text"]).group(3) if boot_a else None
            t = _ota(tb, base, "firmware_b1.bin")
            assert reg.esperar(r"nodo: ota: [1-9]0 %", 90, desde_ts=t), "la descarga no llegó al 10 %"
            c.step("Cortar la salida a Internet: la descarga se queda esperando datos (≤ 30 s, FR-OTA-12)")
            tb.ap_internet(False)
            time.sleep(3)
            c.step("Broker apagado y encendido: T22 aborta con la tarea aún dentro de la lectura")
            t_off = time.time()
            banco.broker_off()
            assert reg.esperar(re.escape("con: OTA_DESCARGA -> CONECTANDO_BROKER (mqtt_down)"), 60, desde_ts=t_off), "sin T22"
            banco.broker_on()
            vuelta = _esperar(sub, base, t_off, lambda s: True, 90)
            assert vuelta, "sin status tras volver el broker"
            c.step("cmd_ota nuevo con la tarea vieja viva: error:red (A3-03)")
            t2 = _ota(tb, base, "firmware_b2.bin")
            seg = _esperar(sub, base, t2, lambda s: s.get("ota") in ("error:red", "en_curso"), 20)
            c.step("Devolver Internet; esperar a que la tarea vieja salga (≤ 30 s)")
            tb.ap_internet(True)
            time.sleep(35)
            c.step("Reset: la imagen abortada no es la de arranque (B-1)")
            t_r = time.time()
            tb.serial_reset(dut_slot)
            boot_r = reg.esperar(BOOT.pattern, 60, desde_ts=t_r)
            assert _esperar(sub, base, t_r, lambda s: True, 150), "sin status tras el reset"
            c.step("cmd_ota de B2 con la tarea vieja ya fuera: termina en fw = B2")
            t3 = _ota(tb, base, "firmware_b2.bin")
            fin = _esperar(sub, base, t3, lambda s: s.get("fw") == B2, 300)
            txt = [e.get("text", "") for e in reg.leer() if e.get("ts", 0) >= t]
        c.save_log("serie", txt)
        boots = [BOOT.search(x) for x in txt if BOOT.search(x)]
        c.note(f"- segundo cmd_ota con la tarea vieja viva: ota = {seg[1].get('ota') if seg else '—'}",
               f"- tras el reset: {boot_r['text'].strip() if boot_r else '—'} (A en {part_a})",
               f"- arranques vistos: {[(b.group(1), b.group(3)) for b in boots]}",
               f"- fw final: {fin[1].get('fw') if fin else '—'}")
        assert any("ota: estado error:red" in x for x in txt), "sin E7 error:red del aborto"
        assert seg and seg[1].get("ota") == "error:red", f"el cmd_ota con la tarea vieja viva no dio error:red: {seg}"
        assert boot_r and BOOT.search(boot_r["text"]).group(1) == a, "tras el aborto, el reset no arrancó A"
        assert BOOT.search(boot_r["text"]).group(3) == part_a, "la imagen abortada quedó como la de arranque (B-1)"
        assert not any(b.group(1) == B1 for b in boots), "B1, abortada, llegó a arrancar"
        assert fin, "el cmd_ota siguiente no terminó en fw = B2"
        c.passed("T22 con la tarea colgada, error:red para el cmd_ota simultáneo, A sigue arrancando y B2 entra después")
