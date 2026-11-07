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
                      _nvs_partition, _parse_flash_args, case, ultimo_arranque)

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
        if firmware["commit"]:   # build de la CI pedido por el test: la versión nombra el commit
            c.note(f"- commit en la versión del arranque: `{firmware['commit']}`")
            assert f"-{firmware['commit']}" in ver, f"la placa no corre el commit {firmware['commit']}: «{ver.strip()}»"
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
AP_PRUEBA = {}                # SSID y clave del AP desechable que el DUT guardó en JRN-01.2 (solo en memoria)
BROKER_BANCO = "192.168.4.1"  # broker mosquitto del banco visto desde su AP (bench-mqtt-broker); sin autenticación


def test_jrn_01_2_provision(testbench, dut_slot, dut_mac, run_dir):
    """JRN-01.2 — el banco aprovisiona por el portal con su AP desechable: T04, T05 y el reinicio en ≤ 5 s."""
    from urllib.parse import urlencode
    from benchlib import credenciales_desechables, esperar_lineas, primera, redactar, unirse_al_portal
    tb = testbench
    ap_ssid, ap_clave = credenciales_desechables()
    AP_PRUEBA.update(ssid=ap_ssid, clave=ap_clave)   # JRN-01.3 levanta este mismo AP
    secretos = [(ap_clave, "<clave-de-prueba>"), (ap_ssid, "<ssid-de-prueba>")]
    ssid = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "JRN-01.2", "Aprovisionar por el portal", run_dir, requires="JRN-01.1") as c:
        c.secretos = secretos
        c.note("- AP desechable del banco con SSID y clave aleatorios de esta ejecución (redactados en la evidencia)",
               f"- broker `{BROKER_BANCO}:1883` (el del banco en la red de su AP, JRN-01.4), sitio `sitio1`, zona `zona1` (ficticios, NFR-SEC-01)", "")
        c.step("Precondiciones: AP del banco apagado; el DUT sigue en PORTAL (JRN-01.1)")
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
        form = {"wifi_ssid": ap_ssid, "wifi_pass": ap_clave, "mqtt_host": BROKER_BANCO, "mqtt_port": "1883",
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
            vistas = esperar_lineas(tb, dut_slot, t_envio, ["con: VALIDANDO -> ARRANQUE (wifi_up)"], timeout=40)
            # El reinicio llega 4 s después de T05 (H-41): se espera un rst:/boot: posterior a T05,
            # no cualquier boot: (el del arranque anterior ya está en el buffer)
            t05_ = primera(vistas, "con: VALIDANDO -> ARRANQUE (wifi_up)")
            fin = time.time() + REINICIO_LIMIT_S + 10
            while t05_ and time.time() < fin and not (primera(vistas, "rst:", desde_ts=t05_["ts"])
                                                     and primera(vistas, "boot: ", desde_ts=t05_["ts"])):
                time.sleep(1)
                vistas = esperar_lineas(tb, dut_slot, t_envio, [], timeout=0)
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
        assert primera(vistas, "portal: POST / -> probando"), "el log no registra la página «probando» servida al envío"
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


# --------------------------------------------------------------------------
# JRN-01.3 · T01, T08 (parte de la Fase 1, FSD 0.9.3), FR-LOG-02
# --------------------------------------------------------------------------
T01_LIMIT_MS = 2000           # T01 (D21): desde la línea boot:
UDP_RETARDO_S = 1.0           # FR-LOG-02
CICLO_S = 60                  # D3: periodo de medición
CICLOS = 3                    # contrato de FR-LOG-02 (fila del receptor)


def _ms(linea):
    m = re.match(r"\w \((\d+)\)", linea)
    return int(m.group(1)) if m else None


def test_jrn_01_3_wifi_and_udp_log(testbench, dut_slot, run_dir):
    """JRN-01.3 — tras el reinicio, el nodo configurado arranca el STA (T01), se une al AP
    del banco y copia su log por UDP al receptor del banco (FR-LOG-02) durante 3 ciclos."""
    from benchlib import esperar_lineas, primera
    tb = testbench
    with case(tb, "JRN-01.3", "Unirse al Wi-Fi y log UDP", run_dir, requires="JRN-01.2") as c:
        assert AP_PRUEBA, "JRN-01.2 no dejó las credenciales del AP desechable"
        c.secretos = [(AP_PRUEBA["clave"], "<clave-de-prueba>"), (AP_PRUEBA["ssid"], "<ssid-de-prueba>")]
        c.note("- el banco levanta el mismo AP desechable que el DUT guardó en JRN-01.2 (redactado)", "")
        c.step("Precondiciones: AP y broker del banco apagados; el DUT quedó configurado (JRN-01.2)")
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
        assert not tb.mqtt_status().get("running"), "el broker del banco está activo: T11 no debe ocurrir en este paso"
        ap_on = False
        try:
            c.step("El banco levanta su AP desechable (canal 1) y resetea el DUT")
            tb.ap_start(AP_PRUEBA["ssid"], AP_PRUEBA["clave"], channel=1); ap_on = True
            t0 = time.time()
            tb.serial_reset(dut_slot)
            vistas = esperar_lineas(tb, dut_slot, t0, ["con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)"], timeout=30)
            t_ip = primera(vistas, "con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)")
            udp = []
            if t_ip:
                c.step(f"Observando {CICLOS} ciclos de medición ({CICLOS * CICLO_S} s) en el log serie y en el receptor UDP")
                time.sleep(CICLOS * CICLO_S + 5)
                vistas = esperar_lineas(tb, dut_slot, t0, [], timeout=0)
                udp = tb.udplog(limit=2000)
        finally:
            if ap_on:
                tb.ap_stop()
        c.save_log("serie", [e["text"] for e in vistas])
        c.save_log("udp", [str(u.get("line", u) if isinstance(u, dict) else u) for u in udp])
        # Solo lo que siguió a nuestro reset: el buffer del banco puede entregar tarde la cola
        # del arranque anterior con marcas de tiempo posteriores a t0
        ult = ultimo_arranque(vistas)   # el último arranque, aunque llegue sin rst: (CR-TB-12)
        assert ult is not None, "la captura no contiene el inicio del arranque tras el reset"
        vistas = vistas[ult:]
        textos = [e["text"] for e in vistas]
        t_ip = primera(vistas, "con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)")

        # T01: boot:, cfg:, con: ARRANQUE -> CONECTANDO_WIFI y el primer intento en ≤ 2 s; sin AP
        boot = primera(vistas, "boot: clima-")
        assert boot, "falta la línea boot:"
        assert primera(vistas, "cfg: sitio=sitio1 zona=zona1"), "falta cfg: sitio=sitio1 zona=zona1 (E2)"
        assert primera(vistas, "con: ARRANQUE -> CONECTANDO_WIFI (fin_arranque)"), "falta T01"
        intento = primera(vistas, "wifi: intento 1")
        assert intento, "falta wifi: intento 1 (E4): T01 no arrancó el STA"
        t01 = _ms(intento["text"]) - _ms(boot["text"])
        c.note(f"- T01: boot: → wifi: intento 1 en {t01} ms (límite {T01_LIMIT_MS} ms)")
        assert 0 <= t01 <= T01_LIMIT_MS, f"T01 en {t01} ms"
        assert not any("softAP" in t for t in textos if "wifi:mode" in t), "T01 abrió el AP (prohibido)"
        assert not primera(vistas, "con: ARRANQUE -> PORTAL"), "el nodo configurado volvió a PORTAL"

        # T08 (Fase 1): su línea con: en ≤ 30 s y sin AP; MQTT y SNTP son de la Fase 2
        assert t_ip, "falta con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up) en 30 s"
        assert not primera(vistas, "con: CONECTANDO_BROKER -> OPERATIVO"), "OPERATIVO sin broker (T11 en la Fase 1)"

        # FR-LOG-02: «UDP logging -> host:port» y cada línea serie en el receptor en ≤ 1 s
        def txt(u): return str(u.get("line", u.get("text", "")) if isinstance(u, dict) else u).strip()   # el receptor da «line»
        def ts(u): return float(u.get("ts", 0)) if isinstance(u, dict) else 0.0
        assert any("UDP logging -> " in txt(u) for u in udp if ts(u) >= t0), "el receptor UDP no recibió UDP logging -> <host>:<port> (E11)"
        # Desde la línea de T08 en el orden en que el DUT escribe (la hora de llegada al banco va a ráfagas)
        tras_ip = [e for e in vistas[vistas.index(t_ip):] if e["text"].strip()]
        perdidas, tarde = [], []
        for e in tras_ip:
            cuerpo = e["text"].strip()   # con su «I (ms)» del DUT: no casa con una línea igual de otro arranque
            m = next((u for u in udp if ts(u) >= t0 and txt(u) == cuerpo), None)
            if not m: perdidas.append(cuerpo)
            elif ts(m) - e["ts"] > UDP_RETARDO_S: tarde.append(cuerpo)
        c.note(f"- {len(tras_ip)} líneas serie tras obtener IP; perdidas {len(perdidas)}, tarde {len(tarde)}")
        assert not perdidas, f"{len(perdidas)} líneas serie sin copia UDP (FR-LOG-02)"
        assert not tarde, f"{len(tarde)} líneas llegaron por UDP más de {UDP_RETARDO_S} s tarde"
        meds = sorted({t.strip() for t in textos if "nodo: med: " in t})   # el buffer del banco puede repetir una línea
        assert len(meds) >= CICLOS, f"solo {len(meds)} ciclos de medición en la ventana"
        c.passed(f"T01 en {t01} ms, unido al AP del banco, log UDP completo en {CICLOS} ciclos")


# --------------------------------------------------------------------------
# JRN-01.4 · T11, FR-MQTT-06, FR-MQTT-08 (Fase 2)
# --------------------------------------------------------------------------
T11_ESPERA_S = 60             # margen de observación desde el reset hasta OPERATIVO (no es un límite del FSD)
TRAS_T11_S = 10               # tiempo de escucha tras OPERATIVO
RESET_VALORES = {"poweron", "ext", "sw", "panic", "task_wdt", "int_wdt", "wdt", "deepsleep",
                 "brownout", "usb", "jtag", "otro"}                                      # §9.3
OTA_VALOR = re.compile(r"^(ninguno|en_curso|ok|rechazado:(payload|host|ruta|misma_version|ocupado)"
                       r"|error:(redirecciones|tls|imagen|http|red))$")                 # §9.3


def _tipos_status(st):
    """Errores de §9.3 en un status: los 9 campos con su tipo (bool no cuenta como entero)."""
    def entero(v): return isinstance(v, int) and not isinstance(v, bool)
    reglas = {
        "estado": lambda v: v == "online",
        "fw": lambda v: isinstance(v, str) and v != "",
        "rssi": lambda v: entero(v) and v < 0,
        "reset": lambda v: v in RESET_VALORES,
        "uptime_s": lambda v: entero(v) and v >= 0,
        "lecturas": lambda v: entero(v) and v >= 0,
        "err_sensor": lambda v: entero(v) and v >= 0,
        "ota": lambda v: isinstance(v, str) and bool(OTA_VALOR.match(v)),
        "hora_valida": lambda v: isinstance(v, bool),
    }
    errores = [f"{k} ausente" for k in reglas if k not in st]
    errores += [f"{k}={st[k]!r}" for k, ok in reglas.items() if k in st and not ok(st[k])]
    errores += [f"campo extra {k}" for k in st if k not in reglas]
    return errores


def test_jrn_01_4_broker_and_status(testbench, dut_slot, dut_mac, run_dir):
    """JRN-01.4 — con el AP y el broker del banco arriba, el nodo pasa a OPERATIVO (T11) y el
    primer mensaje que publica es status online con los 9 campos de §9.3, retenido."""
    import json
    from benchlib import esperar_lineas, primera, suscriptor_mqtt
    tb = testbench
    nodo = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "JRN-01.4", "Conectar al broker y publicar status", run_dir, requires="JRN-01.3") as c:
        assert AP_PRUEBA, "JRN-01.2 no dejó las credenciales del AP desechable"
        c.secretos = [(AP_PRUEBA["clave"], "<clave-de-prueba>"), (AP_PRUEBA["ssid"], "<ssid-de-prueba>")]
        c.note(f"- broker del banco (abierto); tópicos bajo `{base}/`", "")
        c.step("Precondiciones: AP y broker del banco apagados")
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
        assert not tb.mqtt_status().get("running"), "el broker del banco está activo: no es nuestro, no se toca"
        ap_on = broker_on = False
        vivo, retenido, vistas = [], [], []
        try:
            c.step("Arrancar el broker, borrar los retenidos del nodo y suscribirse a sitio1/zona1/#")
            tb.mqtt_start(); broker_on = True
            with suscriptor_mqtt(tb, "sitio1/zona1/#", limpiar=[f"{base}/{m}" for m in
                                 ("status", "temperatura", "humedad", "punto_rocio")]) as sub:
                # Reset ANTES de levantar el AP: el DUT de JRN-01.3 sigue reintentando el Wi-Fi y,
                # con el AP arriba, se uniría y publicaría antes del reset (sesión que no cuenta)
                c.step("Resetear el DUT y levantar el AP desechable (canal 1)")
                t0 = time.time()
                tb.serial_reset(dut_slot)
                tb.ap_start(AP_PRUEBA["ssid"], AP_PRUEBA["clave"], channel=1); ap_on = True
                vistas = esperar_lineas(tb, dut_slot, t0, ["con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up)"],
                                        timeout=T11_ESPERA_S)
                time.sleep(TRAS_T11_S)
                vivo = sub.mensajes()
            c.step("Suscriptor nuevo: el status debe estar retenido")
            with suscriptor_mqtt(tb, f"{base}/status") as sub2:
                time.sleep(3)
                retenido = sub2.mensajes()
            vistas = esperar_lineas(tb, dut_slot, t0, [], timeout=0)
        finally:
            if ap_on:
                tb.ap_stop()
            if broker_on:
                tb.mqtt_stop()
        c.save_log("serie", [e["text"] for e in vistas])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={m['retain']} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in vivo + retenido])
        ult = ultimo_arranque(vistas)   # el último arranque, aunque llegue sin rst: (CR-TB-12)
        assert ult is not None, "la captura no contiene el inicio del arranque tras el reset"
        vistas = vistas[ult:]
        t11 = primera(vistas, "con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up)")
        assert t11, f"sin con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up) en {T11_ESPERA_S} s (T11)"
        del_nodo = [m for m in vivo if m["topic"].startswith(base + "/") and m["payload"] and m["t"] >= t0]
        assert del_nodo, f"ningún mensaje del nodo bajo {base}/ tras T11"
        primero = del_nodo[0]
        # Sesiones MQTT en la ventana: cada status online abre una; un Last Will cierra la anterior
        sesiones = [m for m in del_nodo if m["topic"] == f"{base}/status" and '"online"' in m["payload"]]
        lwt = [m for m in del_nodo if m["payload"] == '{"estado":"offline"}']
        c.note("", "## Resultado", "", f"- primer mensaje: `{primero['topic']}` qos={primero['qos']} a {primero['t'] - t0:+.2f} s del reset",
               f"- payload: `{primero['payload']}`", f"- mensajes del nodo en la ventana: {len(del_nodo)}",
               f"- status online: {len(sesiones)}; Last Will offline: {len(lwt)} (informativo: un segundo arranque daría 2 y 1)")
        assert primero["topic"] == f"{base}/status", f"el primer mensaje es {primero['topic']}, no status (FR-MQTT-06)"
        st = json.loads(primero["payload"])
        errores = _tipos_status(st)
        assert not errores, f"status no cumple §9.3: {errores} (FR-MQTT-08)"
        assert st["uptime_s"] <= primero["t"] - t0 + 2, f"uptime_s={st['uptime_s']}: el status no es de este arranque"
        assert primero["qos"] == 1, f"status con QoS {primero['qos']} (§9.2: QoS 1)"
        ret = [m for m in retenido if m["payload"]]
        assert ret and ret[0]["retain"], "status no quedó retenido en el broker (§9.2)"
        assert json.loads(ret[-1]["payload"]).get("estado") == "online", "el status retenido no dice online"
        c.passed(f"T11, primer mensaje status online con los 9 campos (fw={st['fw']}, reset={st['reset']}), retenido")


# --------------------------------------------------------------------------
# JRN-01.5 · FR-HA-01 (con el Home Assistant de prueba, H-52)
# --------------------------------------------------------------------------
HA_ESPERA_S = 60        # de T11 a ver el dispositivo y sus valores en Home Assistant
UNIDADES_HA = {"temperatura": "°C", "humedad": "%", "punto_rocio": "°C"}


def _ha_resumen(ha, nodo):
    """Dispositivos MQTT de Home Assistant con sus entidades (unidad y valor). La instancia
    es nueva y solo ve el broker del banco: todo dispositivo MQTT es del nodo; dos serían
    un duplicado."""
    devs = ha.dispositivos_mqtt()
    return devs, devs


def _ha_ok(del_nodo):
    """Errores frente a «1 dispositivo con 3 entidades y valores en °C/%»; [] si cumple."""
    if len(del_nodo) != 1:
        return [f"{len(del_nodo)} dispositivos del nodo"]
    (dev,) = del_nodo.values()
    errores = [] if dev["nombre"] == "Clima sitio1 zona1" else [f"nombre {dev['nombre']!r}"]
    ents = dev["entidades"]
    if len(ents) != 3:
        errores.append(f"{len(ents)} entidades")
    unidades = sorted(e["unit"] or "" for e in ents)
    if unidades != sorted(UNIDADES_HA.values()):
        errores.append(f"unidades {unidades}")
    for e in ents:
        try:
            float(e["state"])
        except (TypeError, ValueError):
            errores.append(f"{e['entity_id']} = {e['state']!r}")
    return errores


def _ha_esperar(ha, nodo, timeout):
    fin = time.time() + timeout
    while True:
        devs, del_nodo = _ha_resumen(ha, nodo)
        errores = _ha_ok(del_nodo)
        if not errores or time.time() > fin:
            return devs, del_nodo, errores
        time.sleep(3)


def test_jrn_01_5_home_assistant_discovery(testbench, dut_slot, dut_mac, run_dir):
    """JRN-01.5 — con el broker del banco y el Home Assistant de prueba (laptop, H-52), el nodo
    publica Discovery al conectar y Home Assistant muestra 1 dispositivo con 3 entidades en
    °C/%; tras parar y arrancar el broker una vez y reiniciar el DUT una vez, sin duplicados."""
    from urllib.parse import urlparse
    from benchlib import Registro, suscriptor_mqtt
    from ha_cliente import HomeAssistant
    tb = testbench
    nodo = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    t11 = re.escape("con: CONECTANDO_BROKER -> OPERATIVO (mqtt_up)")
    with case(tb, "JRN-01.5", "Home Assistant descubre el nodo", run_dir, requires="JRN-01.4") as c:
        ha = HomeAssistant()
        c.secretos = [(AP_PRUEBA["clave"], "<clave-de-prueba>"), (AP_PRUEBA["ssid"], "<ssid-de-prueba>")]
        c.note(f"- Home Assistant de prueba {ha.version} en la laptop (Docker de WSL, H-52), instancia nueva", "")
        assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
        assert not tb.mqtt_status().get("running"), "el broker del banco está activo: no es nuestro, no se toca"
        ap_on = broker_on = False
        fases = []
        try:
            c.step("Arrancar el broker, borrar los retenidos de Discovery y añadir la integración MQTT a Home Assistant")
            tb.mqtt_start(); broker_on = True
            with suscriptor_mqtt(tb, f"homeassistant/sensor/{nodo}/#",
                                 limpiar=[f"homeassistant/sensor/{nodo}/{m}/config" for m in UNIDADES_HA]):
                pass
            ha.anadir_mqtt(urlparse(tb.base_url).hostname)
            c.step("Resetear el DUT y levantar el AP; esperar T11 y el dispositivo en Home Assistant")
            t0 = time.time()
            reg = Registro(tb, dut_slot, t0)
            tb.serial_reset(dut_slot)
            tb.ap_start(AP_PRUEBA["ssid"], AP_PRUEBA["clave"], channel=1); ap_on = True
            assert reg.esperar(t11, 130), "sin T11 en 130 s"
            fases.append(("conexión", *_ha_esperar(ha, nodo, HA_ESPERA_S)))
            # Esperas de T11 de 130 s: la captura serie del banco puede retener la última línea
            # hasta la salida siguiente (≤ 1 ciclo de med:); el contrato se observa en Home Assistant
            c.step("Parar el broker 10 s y arrancarlo; esperar T11")
            tb.mqtt_stop(); broker_on = False
            time.sleep(10)
            t_b = time.time()
            tb.mqtt_start(); broker_on = True
            assert reg.esperar(t11, 130, desde_ts=t_b), "sin T11 en 130 s tras volver el broker"
            fases.append(("broker parado y arrancado", *_ha_esperar(ha, nodo, HA_ESPERA_S)))
            c.step("Resetear el DUT; esperar T11")
            t_r = time.time()
            tb.serial_reset(dut_slot)
            assert reg.esperar(t11, 130, desde_ts=t_r + 5), "sin T11 en 130 s tras el reset"
            fases.append(("DUT reiniciado", *_ha_esperar(ha, nodo, HA_ESPERA_S)))
        finally:
            if ap_on:
                tb.ap_stop()
            if broker_on:
                tb.mqtt_stop()
            c.save_log("serie", [e["text"] for e in reg.leer()] if "reg" in locals() else [])
        c.note("", "## Resultado", "")
        for nombre, devs, del_nodo, errores in fases:
            c.note(f"- {nombre}: {len(devs)} dispositivo(s) MQTT; " +
                   "; ".join(f"«{v['nombre']}»: " + ", ".join(f"{e['entity_id']}={e['state']} {e['unit'] or ''}"
                                                            for e in v["entidades"]) for v in devs.values()) +
                   (f" — {errores}" if errores else ""))
        for nombre, devs, del_nodo, errores in fases:
            assert not errores, f"{nombre}: {errores} (FR-HA-01/02)"
            assert len(devs) == 1, f"{nombre}: {len(devs)} dispositivos MQTT (duplicados)"
        c.passed("1 dispositivo «Clima sitio1 zona1» con 3 entidades en °C/% tras conectar, tras el broker y tras el reset")
