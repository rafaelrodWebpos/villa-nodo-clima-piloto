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
