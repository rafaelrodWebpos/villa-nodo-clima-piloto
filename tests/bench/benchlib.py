"""Ayudantes comunes del nivel bench: protocolo de tres fases (panel + evidencia)
y captura de arranque (P-BOOT-CAPTURE). Los usan los JRN y los TC."""
import contextlib
import os
import pathlib
import re
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
PASSED = set()          # pasos del recorrido que han pasado en esta sesión


# --------------------------------------------------------------------------
# Ayudantes
# --------------------------------------------------------------------------
class Case:
    """Panel del banco + evidencia markdown de un paso (protocolo de tres fases)."""

    def __init__(self, tb, tid, name, run_dir):
        self.tb, self.tid, self.name, self.run_dir = tb, tid, name, run_dir
        self.lines = [f"# {tid} — {name}", ""]
        self.result, self.detail = "FAIL", ""
        self.secretos = []        # [(valor, marca)]: se redactan en todo lo que se guarda

    def step(self, text):
        self.tb.test_step(self.tid, self.name, text)   # antes de la acción, nunca después
        self.lines += [f"- {text}"]

    def note(self, *text):
        self.lines += list(text)

    def _r(self, texto):
        for valor, marca in self.secretos:
            if valor:
                texto = texto.replace(valor, marca)
        return redactar_macs(texto)

    def save_log(self, suffix, lines):
        (self.run_dir / f"{self.tid}-{suffix}.log").write_text(self._r("\n".join(lines) + "\n"))
        self.lines += [f"- log: `{self.tid}-{suffix}.log` ({len(lines)} líneas)"]

    def passed(self, detail):
        self.result, self.detail = "PASS", detail
        PASSED.add(self.tid)


@contextlib.contextmanager
def case(tb, tid, name, run_dir, requires=None, spec="JRN-01 villa-nodo-clima-piloto"):
    c = Case(tb, tid, name, run_dir)
    tb.test_start(spec, "Fase 1", total=1)
    try:
        if requires and requires not in PASSED:
            pytest.skip(f"not done: {requires} no ha pasado en esta sesión (workflow)")
        yield c
    except pytest.skip.Exception as e:
        c.result, c.detail = "SKIP", str(e)
        raise
    except Exception as e:
        c.detail = f"{type(e).__name__}: {e}"
        raise
    finally:
        c.detail = c._r(c.detail)
        tb.test_result(tid, name, c.result, c.detail[:200])
        tb.test_end()
        c.lines += ["", f"**Resultado: {c.result}** — {c.detail}", ""]
        (run_dir / f"{tid}.md").write_text(c._r("\n".join(c.lines)))


def _parse_flash_args(coldflash: pathlib.Path) -> dict:
    """{offset: ruta} de coldflash/flash_args (líneas «0x... fichero»).

    flash_args nombra cada imagen con su ruta en build/ (p. ej.
    bootloader/bootloader.bin); build.yml las copia planas a coldflash/."""
    images = {}
    for line in (coldflash / "flash_args").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].startswith("0x"):
            f = coldflash / pathlib.PurePosixPath(parts[1]).name
            assert f.is_file(), f"{parts[1]} de flash_args no está en coldflash/"
            images[parts[0]] = str(f)
    assert images, "flash_args sin imágenes"
    return images


def _nvs_partition() -> tuple:
    """(offset, tamaño) de la partición nvs, de partitions.csv (FSD §2.2)."""
    for line in (REPO / "partitions.csv").read_text().splitlines():
        cols = [c.strip() for c in line.split(",")]
        if cols and cols[0] == "nvs":
            return cols[3], int(cols[4], 16)
    raise AssertionError("partitions.csv sin partición nvs")


def _lines(resp: dict) -> list:
    out = resp.get("output") or resp.get("lines") or []
    return [o.get("text", "") if isinstance(o, dict) else str(o) for o in out]


def _after_last_reset(lines: list) -> list:
    """Solo lo que el DUT escribió tras su último «rst:» de ROM: la respuesta
    del reset puede traer antes la cola del arranque anterior."""
    idx = [i for i, ln in enumerate(lines) if ln.startswith("rst:")]
    return lines[idx[-1]:] if idx else []


# Inicio de un arranque: la línea rst: de la ROM o, si se perdió, cualquiera de las
# primeras líneas de la aplicación, hasta la E1 propia («nodo: boot: clima-»), que
# está en todos. Un solo /api/serial/reset produce hoy DOS arranques: el segundo llega
# ~2,6 s después, sin rst: y a veces sin sus primeras líneas (CR-TB-12).
_INICIO_ARRANQUE = re.compile(r"^rst:|cpu_start: (Multicore app|Pro cpu start user code)|"
                              r"app_init: Project name|nodo: boot: clima-")


def ultimo_arranque(entradas: list) -> int | None:
    """Índice del inicio del último arranque en [{text, ts}] o en líneas; None si no hay."""
    txt = [e.get("text", "") if isinstance(e, dict) else str(e) for e in entradas]
    idx = [i for i, t in enumerate(txt) if _INICIO_ARRANQUE.search(t)]
    return idx[-1] if idx else None


def _boot_capture(tb, slot: str, pattern: str) -> list:
    """P-BOOT-CAPTURE: el reset trae su propio log; si el patrón no está,
    monitor esperando (15 s) y segundo reset."""
    first = tb.serial_reset(slot)
    assert first.get("method") != "jtag", "el reset fue por JTAG: la respuesta es de OpenOCD, no del DUT"
    lines = _lines(first)
    if any(pattern in ln for ln in _after_last_reset(lines)):
        return lines
    seen = {}
    mon = threading.Thread(target=lambda: seen.update(tb.serial_monitor(slot, pattern=pattern, timeout=15)))
    mon.start()
    time.sleep(1)  # el monitor tiene que estar esperando antes del reset
    second = tb.serial_reset(slot)
    mon.join(25)
    return lines + _lines(second) + _lines(seen)


def _boot_ids(lines: list) -> list:
    """<nodo> de cada línea E1 «boot: <nodo> fw=…» (FSD §18)."""
    return [m.group(1) for ln in lines for m in [re.search(r"boot: (\S+) fw=", ln)] if m]




def hora_utc(t: float) -> str:
    """HH:MM:SS.mmm UTC de un instante epoch (para cruzar la evidencia con el log del banco)."""
    return time.strftime("%H:%M:%S", time.gmtime(t)) + f".{int(t * 1000) % 1000:03d}"


def unirse_al_portal(tb, ssid, c, red="192.168.4.", intentos=2):
    """El banco se une al AP abierto del DUT y comprueba que el DHCP del portal
    le dio una IP de su red. sta_join del banco puede volver con una dirección
    link-local (169.254.x.x) si el DHCP no contestó a tiempo; con ella toda
    petición al DUT acaba en timeout. Se reintenta la unión; si no se consigue,
    not done (precondición del banco), nunca failed."""
    for i in range(1, intentos + 1):
        c.step(f"El banco se une al AP abierto {ssid} (intento {i})")
        t = time.time()
        ip = str(tb.sta_join(ssid, timeout=20).get("ip", ""))
        c.note(f"- sta_join intento {i}: ip del banco `{ip}` ({hora_utc(t)} → {hora_utc(time.time())} UTC)")
        if ip.startswith(red):
            return ip
        tb.sta_leave()
        time.sleep(2)
    pytest.skip(f"not done: sta_join no obtuvo IP de {red}0/24 en {intentos} intentos (última {ip})")


_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")


def _mac_permitida():
    """Prefijo de las MAC que pueden quedar en la evidencia: la del DUT (dut.identity,
    publicada por H-20) y las de sus interfaces (STA, softAP), que comparten los 5
    primeros bytes. Cualquier otra (la radio del banco, un teléfono) se redacta."""
    m = re.search(r"^    mac: (\S+)", (REPO / "testing" / "test-plan.yaml").read_text(encoding="utf-8"), re.M)
    return m.group(1).lower()[:14] if m else None


def redactar_macs(texto):
    pre = _mac_permitida()
    return _MAC.sub(lambda m: m.group(0) if pre and m.group(0).lower().startswith(pre) else "<mac>", texto)


def credenciales_desechables():
    """SSID y clave aleatorios para el AP del banco, distintos en cada ejecución.
    Nunca se escriben en el repo ni en la evidencia (se redactan)."""
    import secrets
    ssid = "nodo-prueba-" + secrets.token_hex(3)
    clave = secrets.token_urlsafe(12).replace("-", "a").replace("_", "b")
    return ssid, clave


def redactar(texto, secretos):
    """Sustituye cada secreto (y el SSID desechable) por un marcador antes de guardar evidencia."""
    for valor, marca in secretos:
        if valor:
            texto = texto.replace(valor, marca)
    return texto


def borrar_nvs(tb, slot, tmp_dir):
    """P-NVS-ERASE: escribe 0xFF sobre la partición nvs (partitions.csv). El DUT
    arranca después sin configuración (T02)."""
    off, size = _nvs_partition()
    blank = pathlib.Path(tmp_dir) / "nvs_blank.bin"
    blank.write_bytes(b"\xff" * size)
    res = tb.flash(slot, {off: str(blank)}, chip="esp32s3")
    assert res.get("ok") and res.get("returncode", 0) == 0, f"P-NVS-ERASE falló: {res.get('error') or res}"


def esperar_lineas(tb, slot, since, patrones, timeout):
    """Lee el buffer del slot desde since hasta que aparezcan todos los patrones o
    venza timeout. Devuelve las entradas [{text, ts}] vistas."""
    fin = time.time() + timeout
    vistas = []
    while True:
        out = tb.serial_output(slot, lines=500, since=since)
        vistas = [e if isinstance(e, dict) else {"text": str(e), "ts": 0} for e in (out.get("lines") or [])]
        textos = [e.get("text", "") for e in vistas]
        if all(any(p in t for t in textos) for p in patrones) or time.time() > fin:
            return vistas
        time.sleep(1)


def primera(entradas, patron, desde_ts=0):
    """Primera entrada con patron y ts ≥ desde_ts, o None."""
    return next((e for e in entradas if patron in e.get("text", "") and e.get("ts", 0) >= desde_ts), None)


def aprovisionar(tb, slot, ssid_portal, c, tmp_dir, mqtt_host="broker.local"):
    """Precondición compartida: deja el DUT configurado contra un AP desechable del
    banco nuevo (SSID y clave aleatorios), por el portal, como JRN-01.2: P-NVS-ERASE
    y reset hasta PORTAL, POST válido, AP del banco arriba hasta «nvs: config
    escrita» y el reinicio, y AP abajo. Devuelve (ssid, clave); not done si no se
    llega a guardar. Nunca escribe las credenciales en la evidencia."""
    from urllib.parse import urlencode
    import pytest
    ap_ssid, ap_clave = credenciales_desechables()
    c.secretos = list(getattr(c, "secretos", [])) + [(ap_clave, "<clave-de-prueba>"), (ap_ssid, "<ssid-de-prueba>")]
    assert not tb.ap_status().get("active"), "el AP del banco está activo: no es nuestro, no se toca"
    c.step("Precondiciones: P-NVS-ERASE y reset; el DUT debe arrancar en PORTAL")
    borrar_nvs(tb, slot, tmp_dir)
    boot = _after_last_reset(_boot_capture(tb, slot, "con: ARRANQUE -> PORTAL"))
    if not any("con: ARRANQUE -> PORTAL" in ln for ln in boot):
        pytest.skip("not done: el DUT no arrancó en PORTAL tras P-NVS-ERASE")
    form = {"wifi_ssid": ap_ssid, "wifi_pass": ap_clave, "mqtt_host": mqtt_host, "mqtt_port": "1883",
            "mqtt_user": "", "mqtt_pass": "", "sitio": "sitio1", "zona": "zona1"}
    t_envio = time.time()
    joined = ap_on = False
    try:
        time.sleep(2)
        unirse_al_portal(tb, ssid_portal, c)
        joined = True
        c.step("Precondiciones: POST / con los datos de un AP desechable nuevo")
        r = tb.http_request("POST", "http://192.168.4.1/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                            body=urlencode(form).encode(), timeout=10)
        if r.status_code != 200 or 'id="estado-probando"' not in r.text:
            pytest.skip(f"not done: el envío no respondió «probando» (HTTP {r.status_code})")
        tb.sta_leave(); joined = False
        tb.ap_start(ap_ssid, ap_clave, channel=1); ap_on = True
        vistas = esperar_lineas(tb, slot, t_envio, ["nvs: config escrita", "con: VALIDANDO -> ARRANQUE (wifi_up)"], timeout=40)
    finally:
        if ap_on:
            tb.ap_stop()
        if joined:
            tb.sta_leave()
    if not primera(vistas, "nvs: config escrita"):
        pytest.skip("not done: el DUT no guardó la configuración (sin «nvs: config escrita»)")
    c.note("- precondición: DUT configurado contra un AP desechable nuevo (redactado); AP del banco apagado", "")
    return ap_ssid, ap_clave


class _Suscripcion:
    def __init__(self):
        self._msgs, self._lock = [], __import__("threading").Lock()
        self.conexiones = []     # instantes en que el suscriptor quedó suscrito (tras cada reconexión)

    def guardar(self, msg):
        with self._lock:
            self._msgs.append({"t": time.time(), "topic": msg.topic, "qos": msg.qos, "retain": bool(msg.retain),
                               "payload": msg.payload.decode("utf-8", "replace")})

    def mensajes(self):
        with self._lock:
            return list(self._msgs)

    def conectado(self, t):
        with self._lock:
            self.conexiones.append(t)


@contextlib.contextmanager
def suscriptor_mqtt(tb, filtro, limpiar=()):
    """Cliente MQTT del lado del banco (red de laboratorio) contra el broker del banco: la
    dirección sale de TESTBENCH_URL y nunca se escribe en la evidencia. Antes de suscribirse
    borra los retenidos de `limpiar` (payload vacío, retain) para no confundirlos con los del DUT.
    `filtro` es uno o varios filtros; si el broker se para y vuelve, el cliente se reconecta y se
    vuelve a suscribir (sesión limpia), y `sub.conexiones` guarda cuándo."""
    import paho.mqtt.client as mqtt
    from urllib.parse import urlparse
    host = urlparse(tb.base_url).hostname
    sub = _Suscripcion()
    cli = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"banco-{os.getpid()}-{time.time_ns() % 10**6}",
                      protocol=mqtt.MQTTv311)
    filtros = [filtro] if isinstance(filtro, str) else list(filtro)
    cli.on_message = lambda _c, _u, msg: sub.guardar(msg)

    listo = []      # la primera suscripción va después de borrar los retenidos; las reconexiones, en on_connect

    def al_conectar(c, _u, _f, rc, _p=None):
        if listo and not rc.is_failure:
            c.subscribe([(f, 1) for f in filtros])
            sub.conectado(time.time())
    cli.on_connect = al_conectar
    cli.on_subscribe = lambda *_a: None
    cli.reconnect_delay_set(min_delay=1, max_delay=2)
    fin = time.time() + 15
    while True:
        try:
            cli.connect(host, 1883, keepalive=30)
            break
        except OSError:
            if time.time() > fin:
                raise
            time.sleep(1)
    cli.loop_start()
    try:
        for t in limpiar:
            cli.publish(t, b"", qos=1, retain=True).wait_for_publish(5)
        listo.append(True)
        cli.subscribe([(f, 1) for f in filtros])
        sub.conectado(time.time())
        time.sleep(0.5)
        yield sub
    finally:
        cli.loop_stop()
        cli.disconnect()


class Registro:
    """Log serie del slot leído por tramos desde `desde` (el buffer devuelve como mucho 500
    líneas por petición): acumula [{text, ts}] sin repetir y espera patrones o regex."""

    def __init__(self, tb, slot, desde):
        self.tb, self.slot, self.desde = tb, slot, desde
        self.entradas, self._vistas = [], set()

    def leer(self):
        out = self.tb.serial_output(self.slot, lines=500, since=self.desde)
        for e in out.get("lines") or []:
            e = e if isinstance(e, dict) else {"text": str(e), "ts": 0}
            clave = (e.get("ts", 0), e.get("text", ""))
            if clave not in self._vistas:
                self._vistas.add(clave)
                self.entradas.append(e)
                self.desde = max(self.desde, e.get("ts", 0))
        return self.entradas

    def esperar(self, regex, timeout, desde_ts=0):
        """Primera entrada con ts ≥ desde_ts que casa con regex, o None al vencer timeout."""
        rx = re.compile(regex)
        fin = time.time() + timeout
        while True:
            hit = next((e for e in self.leer() if e.get("ts", 0) >= desde_ts and rx.search(e.get("text", ""))), None)
            if hit or time.time() > fin:
                return hit
            time.sleep(1)
