"""JRN-01 — el recorrido ordinario (testing/test-plan.yaml → tests).

Workflow: los pasos se ejecutan en orden y cada uno parte del estado que deja
el anterior. El fichero es el orden; pytest los recorre de arriba abajo, y un
paso cuyo anterior no pasó queda en not done (skip), nunca en failed.
"""
import pathlib
import re
import threading
import time

import pytest

from benchlib import (_after_last_reset, _boot_capture, _boot_ids, _lines,
                      _nvs_partition, _parse_flash_args, case)

pytestmark = pytest.mark.journey


# --------------------------------------------------------------------------
# JRN-01.0 · C-HW-02
# --------------------------------------------------------------------------
def test_jrn_01_0_flash_ci_image(testbench, dut_slot, firmware, boot_marker,
                                 bench_image_marker, commit_under_test, run_dir, tmp_path):
    """JRN-01.0 · C-HW-02 — la imagen de la CI arranca en SLOT1 con la NVS borrada; el marcador de banco, según la variante."""
    tb = testbench
    with case(tb, "JRN-01.0", "Grabar la imagen de la CI", run_dir) as c:
        c.note(f"- commit bajo prueba: `{commit_under_test}`",
               f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})",
               f"- slot: {dut_slot}", "")
        # Precondiciones
        c.step("Precondiciones: slot presente")
        slot = tb.get_slot(dut_slot)
        if not slot.get("present"):
            pytest.skip(f"not done: {dut_slot} no presente (state {slot.get('state')})")

        # Ejecución: flasheo con los offsets de flash_args + NVS en blanco (P-NVS-ERASE)
        images = _parse_flash_args(firmware["dir"] / "coldflash")
        nvs_off, nvs_size = _nvs_partition()
        assert nvs_off not in images, "flash_args ya escribe en la NVS"
        blank = tmp_path / "nvs_blank.bin"
        blank.write_bytes(b"\xff" * nvs_size)
        images[nvs_off] = str(blank)
        c.note("", "## Flasheo", "", *[f"- `{o}` {pathlib.Path(p).name}"
               for o, p in sorted(images.items(), key=lambda kv: int(kv[0], 16))], "")
        c.step(f"Grabando {len(images)} imágenes en {dut_slot} (NVS en blanco)")
        res = tb.flash(dut_slot, images, chip="esp32s3")
        c.note(f"- respuesta: ok={res.get('ok')} returncode={res.get('returncode')}", "")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"

        # Ejecución: captura del arranque (P-BOOT-CAPTURE)
        c.step(f"Reset y captura del arranque: {bench_image_marker}, {boot_marker}")
        lines = _boot_capture(tb, dut_slot, boot_marker)
        c.note("", "## Arranque", "")
        c.save_log("boot", lines)

        # Resultado
        boot = _after_last_reset(lines)
        assert boot, "la captura no contiene ninguna línea rst: (el reset no se vio)"
        has_marker = any(bench_image_marker in ln for ln in boot)
        has_init = any(boot_marker in ln for ln in boot)
        ver = next((ln for ln in boot if re.search(r"nodo_clima \S+", ln)), "")
        c.note(f"- tras el último `rst:` ({len(boot)} líneas):",
               f"- `{bench_image_marker}`: {'sí' if has_marker else 'NO'}",
               f"- `{boot_marker}`: {'sí' if has_init else 'NO'}",
               f"- versión en el log: `{ver.strip()}`")
        if firmware["variant"] == "bench":
            assert has_marker, f"{bench_image_marker} no aparece en el arranque de la imagen de banco"
        else:  # verify: imagen de producción del tag (release_verify en el plan)
            assert not has_marker, f"{bench_image_marker} aparece en la imagen de producción (C-LOG-01)"
        assert has_init, f"«{boot_marker}» no aparece en el arranque"
        assert firmware["version"] in ver, f"el log no muestra la versión {firmware['version']}"
        mk = bench_image_marker if firmware["variant"] == "bench" else f"sin {bench_image_marker}"
        c.passed(f"{firmware['version']} arranca: {mk} + {boot_marker}")


# --------------------------------------------------------------------------
# JRN-01.1 · T02, FR-POR-01, FR-ID-01
# --------------------------------------------------------------------------
PORTAL_LIMIT_S = 10          # T02 / FR-POR-01 (D21)
ID_RESETS = 3                # FR-ID-01 (bench): 3 reinicios


def test_jrn_01_1_portal_without_config(testbench, dut_slot, dut_mac, run_dir):
    """JRN-01.1 — sin configuración: ARRANQUE -> PORTAL y AP abierto clima-xxxxxx en ≤ 10 s; id estable en 3 reinicios."""
    tb = testbench
    expected_id = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "JRN-01.1", "Portal sin configuración", run_dir, requires="JRN-01.0") as c:
        c.note(f"- slot: {dut_slot}; id esperado (FR-ID-01, MAC de dut.identity): `{expected_id}`", "")
        # Precondiciones: la NVS la dejó en blanco JRN-01.0; la radio del banco, libre para escanear
        c.step("Precondiciones: AP del banco apagado (el escaneo comparte la radio)")
        assert not tb.ap_status().get("active"), \
            "el AP del banco está activo: el escaneo no puede correr (no se apaga aquí: no es nuestro)"

        # Ejecución 1: reset y escaneo en paralelo hasta ver el SSID del nodo
        c.step(f"Reset y escaneo hasta ver {expected_id} (≤ {PORTAL_LIMIT_S} s)")
        reset_out = {}
        t0 = time.time()
        rt = threading.Thread(target=lambda: reset_out.update(tb.serial_reset(dut_slot)))
        rt.start()
        # Un escaneo lanzado a la vez que el reset barre el canal antes de que
        # exista el AP (el DUT lo levanta ~0,6 s tras su rst:). Esperar al
        # buffer del banco tampoco sirve: va segundos por detrás. Se escanea
        # desde t0 + 1 s; el tiempo se mide desde t0 (cota superior).
        time.sleep(1.0)
        found, scans = None, []
        while time.time() - t0 < PORTAL_LIMIT_S + 10:
            nets = tb.scan().get("networks") or []
            t_scan = time.time() - t0
            mine = [n for n in nets if n.get("ssid") == expected_id]
            others = [n for n in nets if str(n.get("ssid", "")).startswith("clima-") and n.get("ssid") != expected_id]
            scans.append((round(t_scan, 1), [(n["ssid"], n["auth"]) for n in mine + others]))
            if mine:
                found = (t_scan, mine[0])
                break
        rt.join(30)
        c.note("", "## Escaneos (solo SSID clima-*)", "", *[f"- t={t} s: {v or 'ninguno'}" for t, v in scans], "")

        # Ejecución 2: log del arranque (respuesta del reset + buffer del slot desde t0)
        buf = tb.serial_output(dut_slot, lines=300, since=t0)
        lines = _lines(reset_out) + ["--- buffer del slot ---"] + _lines(buf)
        c.save_log("boot", lines)
        boot = _after_last_reset(_lines(reset_out)) + _lines(buf)

        # Resultado 1 — T02 y FR-POR-01
        assert found, f"{expected_id} no apareció en {len(scans)} escaneos ({PORTAL_LIMIT_S + 10} s)"
        t_found, net = found
        c.note(f"- `{expected_id}` visto a los {t_found:.1f} s (cota superior desde la petición de reset), auth {net['auth']}")
        assert net["auth"] == "OPEN", f"el AP del portal tiene seguridad {net['auth']} (FR-POR-01: abierto)"
        assert t_found <= PORTAL_LIMIT_S, f"SSID a los {t_found:.1f} s > {PORTAL_LIMIT_S} s (T02/FR-POR-01)"
        con_ln = next((ln for ln in boot if "con: ARRANQUE -> PORTAL (fin_arranque)" in ln), None)
        boot_ln = next((ln for ln in boot if re.search(r"boot: \S+ fw=", ln)), None)
        assert con_ln, "falta «con: ARRANQUE -> PORTAL (fin_arranque)» en el log (T02, E0)"
        assert boot_ln, "falta la línea boot: (E1)"
        # T02: el límite se mide desde la línea boot: (FSD §6.6), en el reloj del DUT («I (<ms>)»)
        ms = lambda ln: int(re.match(r"\w \((\d+)\)", ln).group(1))
        t02_ms = ms(con_ln) - ms(boot_ln)
        c.note(f"- T02 en el reloj del DUT: boot: → con: en {t02_ms} ms (límite {PORTAL_LIMIT_S * 1000} ms)")
        assert 0 <= t02_ms <= PORTAL_LIMIT_S * 1000, f"T02 en {t02_ms} ms > {PORTAL_LIMIT_S} s"
        assert not any("wifi: intento" in ln for ln in boot), "T02 prohíbe intentar el STA: hay «wifi: intento»"
        ids = _boot_ids(boot)[:1]   # respuesta del reset y buffer se solapan: un arranque, un id
        assert ids and ids[0] == expected_id, f"boot: muestra {ids[:1]} en lugar de {expected_id} (FR-ID-01)"

        # Ejecución 3 — FR-ID-01 (bench): el id no cambia en 3 reinicios
        for i in range(2, ID_RESETS + 1):
            c.step(f"FR-ID-01: reinicio {i} de {ID_RESETS}")
            lines_i = _boot_capture(tb, dut_slot, "con: ARRANQUE -> PORTAL")
            c.save_log(f"boot{i}", lines_i)
            ids += _boot_ids(_after_last_reset(lines_i))[:1]
        c.note(f"- ids en {ID_RESETS} arranques: {ids}")
        assert len(ids) == ID_RESETS and set(ids) == {expected_id}, f"id inestable o ausente: {ids} (FR-ID-01)"
        c.passed(f"PORTAL en {t_found:.1f} s, {expected_id} abierto, id estable en {ID_RESETS} arranques")


# --------------------------------------------------------------------------
# JRN-01.2 · T04, T05, FR-POR-06
# --------------------------------------------------------------------------
REINICIO_LIMIT_S = 5          # T05 / FR-POR-06: desde con: VALIDANDO -> ARRANQUE (wifi_up)


@pytest.mark.xfail(strict=True, reason="T04/T05 sin implementar: un envío válido aún no prueba la conexión")
def test_jrn_01_2_provision(testbench, dut_slot, dut_mac, run_dir):
    """JRN-01.2 — el banco aprovisiona por el portal con su AP desechable: T04, T05 y el reinicio en ≤ 5 s."""
    from urllib.parse import urlencode
    from benchlib import credenciales_desechables, esperar_lineas, primera, redactar, unirse_al_portal
    tb = testbench
    ap_ssid, ap_clave = credenciales_desechables()
    secretos = [(ap_clave, "<clave-de-prueba>"), (ap_ssid, "<ssid-de-prueba>")]
    ssid = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "JRN-01.2", "Aprovisionar por el portal", run_dir, requires="JRN-01.1") as c:
        c.note("- AP desechable del banco con SSID y clave aleatorios de esta ejecución (redactados en la evidencia)",
               "- broker `broker.local`, sitio `sitio1`, zona `zona1` (ficticios, NFR-SEC-01)", "")
        c.step("Precondiciones: AP del banco apagado; el DUT sigue en PORTAL (JRN-01.1)")
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
        form = {"wifi_ssid": ap_ssid, "wifi_pass": ap_clave, "mqtt_host": "broker.local", "mqtt_port": "1883",
                "mqtt_user": "", "mqtt_pass": "", "sitio": "sitio1", "zona": "zona1"}
        t_envio = time.time()
        joined, ap_on = False, False
        try:
            unirse_al_portal(tb, ssid, c)
            joined = True
            c.step("POST / con los datos del AP desechable")
            r = tb.http_request("POST", "http://192.168.4.1/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                                body=urlencode(form).encode(), timeout=10)
            probando = 'id="estado-probando"' in r.text
            c.note(f"- respuesta al envío: HTTP {r.status_code}, probando={probando}")
            assert r.status_code == 200 and probando, "el envío válido no responde «Probando la conexión…»"
            # Un solo radio: el banco no espera el resultado del portal, deja el AP del DUT y levanta el suyo
            tb.sta_leave(); joined = False
            c.step("El banco levanta su AP desechable (canal 1); el DUT debe unirse, guardar y reiniciar")
            tb.ap_start(ap_ssid, ap_clave, channel=1); ap_on = True
            vistas = esperar_lineas(tb, dut_slot, t_envio, ["con: VALIDANDO -> ARRANQUE (wifi_up)", "boot: "], timeout=40)
            time.sleep(3)
            vistas = esperar_lineas(tb, dut_slot, t_envio, ["con: VALIDANDO -> ARRANQUE (wifi_up)"], timeout=1)
        finally:
            if ap_on:
                tb.ap_stop()
            if joined:
                tb.sta_leave()
        c.save_log("log", [redactar(e["text"], secretos) for e in vistas])
        t04 = primera(vistas, "con: PORTAL -> VALIDANDO (envío)")
        nvs = primera(vistas, "nvs: config escrita")
        t05 = primera(vistas, "con: VALIDANDO -> ARRANQUE (wifi_up)")
        assert t04, "falta con: PORTAL -> VALIDANDO (envío) (T04)"
        assert not primera(vistas, "con: VALIDANDO -> PORTAL"), "T06: el DUT no se unió al AP del banco"
        assert t05, "falta con: VALIDANDO -> ARRANQUE (wifi_up) (T05)"
        assert nvs and nvs["ts"] <= t05["ts"], "T05 sin nvs: config escrita antes de reiniciar"
        rst = primera(vistas, "rst:", desde_ts=t05["ts"])
        boot = primera(vistas, "boot: ", desde_ts=t05["ts"])
        assert rst and boot, "el DUT no reinició tras T05"
        dt = rst["ts"] - t05["ts"]
        c.note(f"- T04 → T05 en {t05['ts'] - t04['ts']:.1f} s; reinicio (rst:) a los {dt:.1f} s de T05 (límite {REINICIO_LIMIT_S} s)")
        assert dt <= REINICIO_LIMIT_S, f"reinicio a los {dt:.1f} s de T05"
        c.passed(f"aprovisionado: T04 → T05, nvs: config escrita, reinicio a los {dt:.1f} s")
