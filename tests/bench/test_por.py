"""TC-POR-* — portal cautivo (FSD §11), nivel bench. Atómicos: cada uno
establece y comprueba su propia precondición; la comparten por procedimientos,
nunca por el orden de ejecución."""
import re
import time

import pytest

from benchlib import (_after_last_reset, _boot_capture, _boot_ids, _lines, borrar_nvs, case,
                      credenciales_desechables, esperar_lineas, hora_utc, primera, redactar, unirse_al_portal)

PORTAL_IP = "192.168.4.1"          # FSD §11.1: el servidor del portal
NAMES_17 = {"wifi_ssid", "wifi_pass", "mqtt_host", "mqtt_port",
            "mqtt_user", "mqtt_pass", "zona", "sitio"}
SECRETOS = {"wifi_pass", "mqtt_pass"}


def _en_portal(tb, slot, c, tmp_dir=None):
    """Precondición: el DUT arranca en PORTAL. Si arranca configurado (p. ej., tras
    JRN-01.2), se establece con P-NVS-ERASE y otro reset. Si aun así no, not done."""
    c.step("Precondiciones: reset; el DUT debe arrancar en PORTAL")
    boot = _after_last_reset(_boot_capture(tb, slot, "con: ARRANQUE -> PORTAL"))
    if tmp_dir and not any("con: ARRANQUE -> PORTAL" in ln for ln in boot):
        c.step("Precondiciones: el DUT tiene configuración; P-NVS-ERASE y reset")
        borrar_nvs(tb, slot, tmp_dir)
        boot = _after_last_reset(_boot_capture(tb, slot, "con: ARRANQUE -> PORTAL"))
    ids = _boot_ids(boot)
    fw = next((m.group(1) for ln in boot for m in [re.search(r"boot: \S+ fw=(\S+)", ln)] if m), "?")
    if not any("con: ARRANQUE -> PORTAL" in ln for ln in boot) or not ids:
        pytest.skip("not done: el DUT no arrancó en PORTAL ni tras P-NVS-ERASE")
    c.note(f"- DUT en PORTAL: `{ids[0]}`, fw `{fw}`")
    return ids[0]


def test_tc_por_02_get_form(testbench, dut_slot, run_dir, tmp_path):
    """TC-POR-02 · FR-POR-03 (bench) — GET / sirve los 8 campos de §17, sin secretos rellenos."""
    tb = testbench
    with case(tb, "TC-POR-02", "GET / sirve el formulario", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        ssid = _en_portal(tb, dut_slot, c, tmp_path)
        assert not tb.ap_status().get("active"), "el AP del banco está activo: la radio no puede unirse al DUT"
        time.sleep(2)
        joined = False
        try:
            unirse_al_portal(tb, ssid, c)
            joined = True
            # bench-portal-driver: unirse no debe desplazar la ruta de eth0 (la API sigue respondiendo)
            tb.info()
            c.note("- la API del banco sigue respondiendo tras sta_join (ruta de eth0 intacta)")
            c.step(f"GET http://{PORTAL_IP}/ por el relé HTTP del banco")
            r = tb.http_get(f"http://{PORTAL_IP}/", timeout=10)
        finally:
            if joined:
                tb.sta_leave()
        html = r.text
        (run_dir / "TC-POR-02-get.html").write_text(html)
        c.note(f"- respuesta: HTTP {r.status_code}, {len(html)} bytes, `TC-POR-02-get.html`")
        assert r.status_code == 200, f"GET / devolvió {r.status_code}"
        inputs = re.findall(r"<input\b[^>]*>", html)
        names = {m.group(1) for t in inputs for m in [re.search(r'\bname="([^"]+)"', t)] if m}
        c.note(f"- campos (name): {sorted(names)}")
        assert names == NAMES_17, f"campos {sorted(names)} ≠ §17 {sorted(NAMES_17)}"
        for t in inputs:
            n = re.search(r'\bname="([^"]+)"', t).group(1)
            if n in SECRETOS:
                assert 'type="password"' in t, f"{n} no es password"
                assert not re.search(r'\bvalue="[^"]+"', t), f"{n} vuelve relleno (FR-POR-03, «No debe ocurrir»)"
        c.passed(f"GET / en {ssid}: los 8 campos de §17, secretos vacíos")


# Valores ficticios (nunca datos del banco ni de la vivienda): ningún envío es válido
BASE_FORM = {"wifi_ssid": "red-de-prueba", "wifi_pass": "clave-de-prueba",
             "mqtt_host": "broker.local", "mqtt_port": "1883", "mqtt_user": "",
             "mqtt_pass": "", "sitio": "sitio1", "zona": "zona1"}
ENVIOS_INVALIDOS = [
    ("zona con mayúscula y #", {"zona": "Zona#1"}, {"zona"}),
    ("wifi_pass de 7 caracteres", {"wifi_pass": "corta77"}, {"wifi_pass"}),
]


def test_tc_por_05_invalid_submit(testbench, dut_slot, run_dir, tmp_path):
    """TC-POR-05 · FR-POR-04 (bench) — un envío inválido se responde con el error del campo y no toca la NVS."""
    from urllib.parse import urlencode
    tb = testbench
    with case(tb, "TC-POR-05", "Envío inválido por el portal", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        ssid = _en_portal(tb, dut_slot, c, tmp_path)
        assert not tb.ap_status().get("active"), "el AP del banco está activo: la radio no puede unirse al DUT"
        time.sleep(2)
        t_envio = time.time()
        joined, respuestas = False, []
        try:
            unirse_al_portal(tb, ssid, c)
            joined = True
            for i, (desc, cambios, esperados) in enumerate(ENVIOS_INVALIDOS, 1):
                form = dict(BASE_FORM, **cambios)
                c.step(f"POST / con {desc}")
                t = time.time()
                r = tb.http_request("POST", f"http://{PORTAL_IP}/",
                                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                                    body=urlencode(form).encode(), timeout=10)
                respuestas.append((desc, form, esperados, r, time.time() - t))
                (run_dir / f"TC-POR-05-post{i}.html").write_text(r.text)
        finally:
            if joined:
                tb.sta_leave()

        # Resultado 1 — la respuesta nombra el campo, conserva lo no secreto, nunca los secretos
        for desc, form, esperados, r, dt in respuestas:
            html = r.text
            errores = set(re.findall(r'id="err-([a-z_]+)"', html))
            c.note(f"- {desc}: HTTP {r.status_code} en {dt:.2f} s (ida y vuelta por el relé); errores {sorted(errores)}")
            assert r.status_code == 200, f"{desc}: POST / devolvió {r.status_code}"
            assert errores == esperados, f"{desc}: errores en {sorted(errores)}, esperados {sorted(esperados)}"
            assert 'class="aviso"' in html, f"{desc}: falta el aviso general"
            for n in ("wifi_ssid", "mqtt_host", "sitio", "zona"):
                assert f'value="{form[n]}"' in html, f"{desc}: no conserva {n}"
            for n in SECRETOS:
                if form[n]:
                    assert form[n] not in html, f"{desc}: {n} vuelve relleno"

        # Resultado 2 — una autotransición T03 por envío y ninguna escritura en la NVS
        buf = _lines(tb.serial_output(dut_slot, lines=400, since=t_envio))
        c.step("Reset: el DUT debe volver a PORTAL sin configuración escrita")
        tras = _after_last_reset(_boot_capture(tb, dut_slot, "con: ARRANQUE -> PORTAL"))
        c.save_log("log", buf + ["--- reset ---"] + tras)
        n_t03 = sum("con: PORTAL -> PORTAL (envío)" in ln for ln in buf)
        c.note(f"- `con: PORTAL -> PORTAL (envío)`: {n_t03} de {len(ENVIOS_INVALIDOS)} envíos")
        assert n_t03 == len(ENVIOS_INVALIDOS), f"{n_t03} líneas T03 para {len(ENVIOS_INVALIDOS)} envíos"
        n_log = sum("portal: POST / -> errores" in ln for ln in buf)
        c.note(f"- `portal: POST / -> errores`: {n_log} de {len(ENVIOS_INVALIDOS)}")
        assert n_log == len(ENVIOS_INVALIDOS), f"{n_log} líneas de página servida para {len(ENVIOS_INVALIDOS)} envíos"
        assert not any("nvs: config escrita" in ln for ln in buf + tras), "nvs: config escrita tras un envío inválido"
        assert any("con: ARRANQUE -> PORTAL (fin_arranque)" in ln for ln in tras), "tras el reset no vuelve a PORTAL"
        c.passed(f"{len(ENVIOS_INVALIDOS)} envíos inválidos: error en su campo, sin NVS; reset → PORTAL")


def test_tc_por_07_captive_redirects(testbench, dut_slot, run_dir, tmp_path):
    """TC-POR-07 · FR-POR-02 (bench, parte HTTP) — /generate_204 y /hotspot-detect.html llevan al portal.

    El relé del banco sigue las redirecciones (urllib), así que el 302 no se ve:
    se observa que la respuesta final es el formulario del portal y nunca 204.
    El Location exacto lo verifica TC-POR-06 (host)."""
    tb = testbench
    with case(tb, "TC-POR-07", "Redirecciones del portal cautivo", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        t_ini = time.time()
        ssid = _en_portal(tb, dut_slot, c, tmp_path)
        assert not tb.ap_status().get("active"), "el AP del banco está activo: la radio no puede unirse al DUT"
        time.sleep(2)
        joined, respuestas = False, []
        try:
            unirse_al_portal(tb, ssid, c)
            joined = True
            for ruta in ("/generate_204", "/hotspot-detect.html"):
                c.step(f"GET http://{PORTAL_IP}{ruta}")
                t = time.time()
                try:
                    r = tb.http_get(f"http://{PORTAL_IP}{ruta}", timeout=10)
                finally:
                    c.note(f"- GET {ruta}: {hora_utc(t)} → {hora_utc(time.time())} UTC")
                respuestas.append((ruta, r))
                (run_dir / f"TC-POR-07{ruta.replace('/', '-').replace('.', '_')}.html").write_text(r.text)
        finally:
            if joined:
                tb.sta_leave()
            # Log serie con la hora del banco y cada arranque del DUT (CR-TB-12: dos por reset)
            vistas = esperar_lineas(tb, dut_slot, t_ini, [], timeout=0)
            c.save_log("serie", [f"{hora_utc(e.get('ts', 0))} {e.get('text', '')}" for e in vistas])
            arranques = [e for e in vistas if re.search(r"^rst:|nodo: boot: ", e.get("text", ""))]
            c.note("- arranques del DUT (hora del banco, UTC):",
                   *[f"  - {hora_utc(e.get('ts', 0))} `{e['text'].strip()[:90]}`" for e in arranques])
        for ruta, r in respuestas:
            names = {m.group(1) for t in re.findall(r"<input\b[^>]*>", r.text)
                     for m in [re.search(r'\bname="([^"]+)"', t)] if m}
            c.note(f"- {ruta}: respuesta final HTTP {r.status_code}, {len(r.text)} bytes, formulario={names == NAMES_17}")
            assert r.status_code != 204, f"{ruta}: 204 (el teléfono no mostraría el portal)"
            assert r.status_code == 200 and names == NAMES_17, f"{ruta}: la respuesta final no es el formulario del portal (HTTP {r.status_code})"
        c.passed("/generate_204 y /hotspot-detect.html terminan en el formulario del portal")


def test_tc_por_09_wrong_password(testbench, dut_slot, run_dir, tmp_path):
    """TC-POR-09 · FR-POR-05, T06 (bench) — clave Wi-Fi errónea: «no se pudo conectar» en ≤ 20 s (+5),
    el AP sigue visible y la NVS sin cambios."""
    from urllib.parse import urlencode
    tb = testbench
    ap_ssid, ap_clave = credenciales_desechables()
    mala = ap_clave + "x"
    secretos = [(mala, "<clave-erronea>"), (ap_clave, "<clave-de-prueba>"), (ap_ssid, "<ssid-de-prueba>")]
    with case(tb, "TC-POR-09", "Clave Wi-Fi errónea", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        c.secretos = secretos
        ssid = _en_portal(tb, dut_slot, c, tmp_path)
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
        time.sleep(2)
        form = dict(BASE_FORM, wifi_ssid=ap_ssid, wifi_pass=mala)
        t_envio = time.time()
        joined, ap_on = False, False
        try:
            unirse_al_portal(tb, ssid, c)
            joined = True
            c.step("POST / válido con la clave errónea del AP desechable del banco")
            r = tb.http_request("POST", f"http://{PORTAL_IP}/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                                body=urlencode(form).encode(), timeout=10)
            probando = 'id="estado-probando"' in r.text
            c.note(f"- respuesta al envío: HTTP {r.status_code}, probando={probando}")
            assert r.status_code == 200 and 'id="estado-probando"' in r.text, "el envío válido no responde «Probando la conexión…»"
            tb.sta_leave(); joined = False
            c.step("El banco levanta su AP desechable (canal 1) con la clave correcta")
            tb.ap_start(ap_ssid, ap_clave, channel=1); ap_on = True
            vistas = esperar_lineas(tb, dut_slot, t_envio, ["con: VALIDANDO -> PORTAL (wifi_down)"], timeout=35)
        finally:
            if ap_on:
                tb.ap_stop()
            if joined:
                tb.sta_leave()
        textos = [e["text"] for e in vistas]
        ini = primera(vistas, "con: PORTAL -> VALIDANDO (envío)")
        fin = primera(vistas, "con: VALIDANDO -> PORTAL (wifi_down)")
        assert ini, "falta con: PORTAL -> VALIDANDO (envío) (T04)"
        assert fin, "falta con: VALIDANDO -> PORTAL (wifi_down) en 35 s (T06)"
        dt = fin["ts"] - ini["ts"]
        c.note(f"- T06 a los {dt:.1f} s de T04 (límite 20 s + 5 s por el cambio de canal)")
        assert dt <= 25, f"«no se pudo conectar» a los {dt:.1f} s"
        assert not any("nvs: config escrita" in t for t in textos), "T06 persistió la configuración"

        c.step("El AP del portal sigue visible: el banco vuelve a unirse y pide /")
        time.sleep(2)
        try:
            unirse_al_portal(tb, ssid, c); joined = True
            g = tb.http_get(f"http://{PORTAL_IP}/", timeout=10)
        finally:
            if joined:
                tb.sta_leave()
        (run_dir / "TC-POR-09-get.html").write_text(redactar(g.text, secretos))
        no_conecta = 'id="no-conecta"' in g.text
        c.note(f"- GET / tras T06: HTTP {g.status_code}, no-conecta={no_conecta}")
        assert g.status_code == 200 and 'id="no-conecta"' in g.text, "la página no muestra «No se pudo conectar…»"
        assert f'value="{ap_ssid}"' in g.text, "no conserva la red"
        assert mala not in g.text, "la clave vuelve rellena"
        c.step("Reset: la NVS sigue sin configuración")
        tras = _after_last_reset(_boot_capture(tb, dut_slot, "con: ARRANQUE -> PORTAL"))
        c.save_log("log", [redactar(t, secretos) for t in textos + ["--- reset ---"] + tras])
        assert any("con: ARRANQUE -> PORTAL (fin_arranque)" in ln for ln in tras), "tras el reset no vuelve a PORTAL"
        c.passed(f"clave errónea: T06 a los {dt:.1f} s, AP visible, «no se pudo conectar», NVS sin cambios")


def test_tc_por_11_no_portal_when_configured(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-POR-11 · FR-POR-07 (bench) — configurado (CONECTANDO_WIFI o posterior): ningún SSID clima-*
    en el escaneo y GET http://<ip-dut>/ rechazado, sin respuesta HTTP."""
    from benchlib import _parse_flash_args, aprovisionar
    tb = testbench
    ssid_portal = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "TC-POR-11", "Sin portal fuera de PORTAL y VALIDANDO", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot}")
        res = tb.flash(dut_slot, _parse_flash_args(firmware["dir"] / "coldflash"), chip="esp32s3")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"
        ap_ssid, ap_clave = aprovisionar(tb, dut_slot, ssid_portal, c, tmp_path)
        # 1. CONECTANDO_WIFI (AP del banco apagado): escaneo sin clima-*
        c.step("Reset con el AP apagado (CONECTANDO_WIFI) y escaneo")
        t0 = time.time()
        tb.serial_reset(dut_slot)
        time.sleep(5)
        nets = tb.scan().get("networks") or []
        clima = sorted({n.get("ssid") for n in nets if str(n.get("ssid", "")).startswith("clima-")})
        hay_redes = len(nets)
        # 2. CONECTANDO_BROKER (con IP en la red del banco): GET a la IP del DUT
        ap_on = False
        try:
            c.step("El banco levanta el AP desechable; tras T08, GET http://<ip-dut>/ por el relé")
            tb.ap_start(ap_ssid, ap_clave, channel=1); ap_on = True
            vistas = esperar_lineas(tb, dut_slot, t0, ["con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)"], timeout=90)
            ipl = next((m.group(1) for e in vistas for m in [re.search(r"sta ip: (192\.168\.4\.\d+)", e["text"])] if m), None)
            control = rechazo = None
            if ipl:
                time.sleep(3)
                try:   # control positivo: el relé llega a la red del AP (el propio banco en 192.168.4.1)
                    control = tb.http_get("http://192.168.4.1:8080/api/info", timeout=5).status_code
                except Exception as e:
                    control = f"error {type(e).__name__}"
                try:
                    r = tb.http_get(f"http://{ipl}/", timeout=5)
                    rechazo = ("respuesta", r.status_code)
                except Exception as e:
                    rechazo = ("sin respuesta", str(e)[:160])
        finally:
            if ap_on:
                tb.ap_stop()
        vistas = esperar_lineas(tb, dut_slot, t0, [], timeout=0)
        c.save_log("serie", [c._r(e["text"]) for e in vistas])
        c.note("", "## Resultado", "", f"- escaneo en CONECTANDO_WIFI: {hay_redes} redes, clima-*: {clima or 'ninguna'}",
               f"- IP del DUT tras T08: `{ipl}`", f"- control positivo del relé (GET al banco por la red del AP): {control}",
               f"- GET http://<ip-dut>/: {rechazo}")
        assert hay_redes > 0, "el escaneo no vio ninguna red: no sirve como observación (control positivo)"
        assert ssid_portal not in clima, "el AP del portal aparece con el nodo configurado"
        assert ipl, "el DUT no obtuvo IP en la red del banco (T08 no llegó)"
        assert control == 200, f"el relé no llega a la red del AP ({control}): la observación del rechazo sería nula"
        assert rechazo and rechazo[0] == "sin respuesta", f"el DUT respondió por HTTP fuera del portal: {rechazo}"
        c.passed(f"sin clima-* en el escaneo y GET a {ipl} sin respuesta HTTP")
