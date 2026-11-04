"""TC-POR-* — portal cautivo (FSD §11), nivel bench. Atómicos: cada uno
establece y comprueba su propia precondición; la comparten por procedimientos,
nunca por el orden de ejecución."""
import re
import time

import pytest

from benchlib import _after_last_reset, _boot_capture, _boot_ids, case

PORTAL_IP = "192.168.4.1"          # FSD §11.1: el servidor del portal
NAMES_17 = {"wifi_ssid", "wifi_pass", "mqtt_host", "mqtt_port",
            "mqtt_user", "mqtt_pass", "zona", "sitio"}
SECRETOS = {"wifi_pass", "mqtt_pass"}


def _en_portal(tb, slot, c):
    """Precondición: el DUT arranca en PORTAL (NVS sin configuración). Si no,
    not done: el resultado no diría nada del portal."""
    c.step("Precondiciones: reset; el DUT debe arrancar en PORTAL")
    boot = _after_last_reset(_boot_capture(tb, slot, "con: ARRANQUE -> PORTAL"))
    ids = _boot_ids(boot)
    fw = next((m.group(1) for ln in boot for m in [re.search(r"boot: \S+ fw=(\S+)", ln)] if m), "?")
    if not any("con: ARRANQUE -> PORTAL" in ln for ln in boot) or not ids:
        pytest.skip("not done: el DUT no arrancó en PORTAL (¿NVS con configuración?); P-NVS-ERASE primero")
    c.note(f"- DUT en PORTAL: `{ids[0]}`, fw `{fw}`")
    return ids[0]


def test_tc_por_02_get_form(testbench, dut_slot, run_dir):
    """TC-POR-02 · FR-POR-03 (bench) — GET / sirve los 8 campos de §17, sin secretos rellenos."""
    tb = testbench
    with case(tb, "TC-POR-02", "GET / sirve el formulario", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        ssid = _en_portal(tb, dut_slot, c)
        assert not tb.ap_status().get("active"), "el AP del banco está activo: la radio no puede unirse al DUT"
        time.sleep(2)
        c.step(f"El banco se une al AP abierto {ssid}")
        joined = False
        try:
            j = tb.sta_join(ssid, timeout=20)
            joined = True
            c.note(f"- sta_join: ip del banco en la red del portal `{j.get('ip', '?')}`")
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


def test_tc_por_05_invalid_submit(testbench, dut_slot, run_dir):
    """TC-POR-05 · FR-POR-04 (bench) — un envío inválido se responde con el error del campo y no toca la NVS."""
    from urllib.parse import urlencode
    from benchlib import _lines
    tb = testbench
    with case(tb, "TC-POR-05", "Envío inválido por el portal", run_dir, spec="TC-POR villa-nodo-clima-piloto") as c:
        ssid = _en_portal(tb, dut_slot, c)
        assert not tb.ap_status().get("active"), "el AP del banco está activo: la radio no puede unirse al DUT"
        time.sleep(2)
        t_envio = time.time()
        c.step(f"El banco se une al AP abierto {ssid}")
        joined, respuestas = False, []
        try:
            tb.sta_join(ssid, timeout=20)
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
        assert not any("nvs: config escrita" in ln for ln in buf + tras), "nvs: config escrita tras un envío inválido"
        assert any("con: ARRANQUE -> PORTAL (fin_arranque)" in ln for ln in tras), "tras el reset no vuelve a PORTAL"
        c.passed(f"{len(ENVIOS_INVALIDOS)} envíos inválidos: error en su campo, sin NVS; reset → PORTAL")
