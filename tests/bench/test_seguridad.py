"""Puerta de seguridad S1 (FSD 0.9.8, §3.5) — filas de banco. Atómicos: cada test graba la
imagen de la CI y aprovisiona contra un AP desechable nuevo del banco.

TC-CON-14 · FR-CON-07 (SEC-07): «evil twin». El DUT está configurado contra el AP desechable
del banco, con clave. El banco levanta en su lugar un AP ABIERTO con el MISMO SSID de prueba
(el aleatorio de esta ejecución, nunca el SSID de la casa, H-83): el DUT no debe unirse. Después
vuelve el AP con clave y el DUT debe llegar a T08."""
import re
import time

import pytest

from benchlib import Registro, case
from test_mqtt import _nodo, configurado

T08 = "con: CONECTANDO_WIFI -> CONECTANDO_BROKER (wifi_up)"
GEMELO_S = 180                 # AP abierto gemelo: 3 min (FR-CON-07, §6.6)
VUELTA_S = 90                  # con el AP con clave otra vez: T08 en ≤ 90 s (FR-CON-03)
INTENTOS_MIN = 3               # control positivo: el DUT sigue intentando unirse durante el gemelo


def _estaciones(tb):
    st = tb.ap_status()
    return st, [s.get("mac", "").lower() for s in st.get("stations") or []]


def test_tc_con_14_open_twin_rejected(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-14 · FR-CON-07 — con clave configurada, el DUT no se une a un AP abierto con el
    mismo SSID; con el AP con clave, T08 en ≤ 90 s."""
    tb = testbench
    with case(tb, "TC-CON-14", "AP abierto gemelo (evil twin) rechazado", run_dir,
              spec="TC-CON villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        c.note(f"- AP gemelo: el mismo SSID de prueba de esta ejecución, abierto, {GEMELO_S} s "
               "(nunca el SSID de la casa, H-83)", "")
        c.step(f"Resetear el DUT y levantar el AP ABIERTO gemelo con el SSID de prueba ({GEMELO_S} s)")
        t0 = time.time()
        reg = Registro(tb, dut_slot, t0)
        tb.serial_reset(dut_slot)
        tb.ap_start(banco.ssid, "", channel=1)           # sin clave = abierto
        banco.ap = True
        st, _ = _estaciones(tb)
        assert st.get("active") and st.get("ssid") == banco.ssid, "precondición: el AP gemelo abierto no está activo"
        vistas, fin = set(), time.time() + GEMELO_S
        while time.time() < fin:
            _, macs = _estaciones(tb)
            vistas.update(macs)
            time.sleep(10)
        ent = reg.leer()
        txt = [e.get("text", "") for e in ent]
        intentos = [t for t in txt if re.search(r"nodo: wifi: intento \d+", t)]
        unido = [t for t in txt if T08 in t]
        asociado = dut_mac.lower() in vistas
        c.note(f"- con el gemelo abierto: {len(intentos)} líneas `wifi: intento`; T08: {len(unido)}; "
               f"MAC del DUT entre las estaciones del AP: {'sí' if asociado else 'no'}")
        assert len(intentos) >= INTENTOS_MIN, (
            f"control positivo: solo {len(intentos)} intentos de unión en {GEMELO_S} s; el test no prueba nada")
        assert not unido, "el DUT se unió al AP abierto gemelo (T08)"
        assert not asociado, "el DUT aparece asociado al AP abierto gemelo"

        c.step("Apagar el gemelo y levantar el AP con clave; esperar T08")
        banco.ap_off()
        t_v = time.time()
        banco.ap_on()
        hit = reg.esperar(re.escape(T08), VUELTA_S + 30, desde_ts=t_v)
        c.save_log("serie", [e.get("text", "") for e in reg.leer()])
        assert hit, f"sin T08 en {VUELTA_S + 30} s con el AP con clave"
        dt = hit["ts"] - t_v
        c.note(f"- con el AP con clave: T08 a {dt:.1f} s")
        assert dt <= VUELTA_S, f"T08 a {dt:.1f} s, límite {VUELTA_S} s"
        c.passed(f"gemelo abierto rechazado {GEMELO_S} s ({len(intentos)} intentos, sin asociación); "
                 f"con clave, T08 a {dt:.1f} s")


# --------------------------------------------------------------------------
# TC-POR-12 · FR-POR-08, T24 (SEC-04): el portal se cierra a los 10 min (ESPERA)
# --------------------------------------------------------------------------
T02_LINEA = "con: ARRANQUE -> PORTAL (fin_arranque)"
T24_LINEA = "con: PORTAL -> ESPERA (portal_vence)"
DNS_DETENIDO = "portal: dns detenido"     # E14 (FSD 0.9.9, N-01)
DNS_NO_DISPONIBLE = "portal: dns no disponible"   # E14 (N-03): el DNS no se pudo ligar en T02
DNS_MAX_MS = 5_000
PORTAL_MS, TOL_MS = 600_000, 5_000        # D24: 10 min desde T02, ± 5 s (FSD §6.6)
ESCANEOS_TRAS = 3


def _ms(texto):
    m = re.match(r"\s*[IWE] \((\d+)\)", texto)
    return int(m.group(1)) if m else None


def _visible(tb, ssid):
    return any(n.get("ssid") == ssid for n in tb.scan().get("networks") or [])


def test_tc_por_12_portal_closes_after_10_min(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-POR-12 · FR-POR-08, T24 — sin configuración, el portal se cierra a 600 s ± 5 s de T02:
    el AP desaparece, la medición sigue, nada en la NVS y sin reinicio; otro reset lo reabre."""
    from benchlib import borrar_nvs
    from consola import quitar_relecturas, reinicios
    from test_mqtt import grabar
    tb = testbench
    nodo = _nodo(dut_mac)
    with case(tb, "TC-POR-12", "Portal cerrado a los 10 min (ESPERA)", run_dir,
              spec="TC-POR villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        assert not tb.ap_status().get("active"), "el AP del banco está activo: el escaneo comparte la radio"
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot} y P-NVS-ERASE")
        grabar(tb, dut_slot, firmware, c)
        borrar_nvs(tb, dut_slot, tmp_path)
        c.step("Reset; el DUT abre el portal (T02)")
        t0 = time.time()
        reg = Registro(tb, dut_slot, t0)
        tb.serial_reset(dut_slot)
        assert reg.esperar(re.escape(T02_LINEA), 60), "sin T02 tras el reset"
        time.sleep(30)
        antes = _visible(tb, nodo)
        c.note(f"- a ~30 s de T02, `{nodo}` visible en el escaneo: {'sí' if antes else 'no'}")
        assert antes, "control positivo: el AP del portal no se ve antes del cierre"

        c.step("Esperar el cierre del portal (T24, ≈ 10 min desde T02)")
        hit = reg.esperar(re.escape(T24_LINEA), 720)
        assert hit, "sin «con: PORTAL -> ESPERA (portal_vence)» en 12 min"
        tras = [_visible(tb, nodo) for _ in range(ESCANEOS_TRAS)]
        time.sleep(75)                                    # un ciclo de medición después del cierre
        ent, _ = quitar_relecturas(reg.leer())
        txt = [e.get("text", "") for e in ent]
        i24 = next(i for i, t in enumerate(txt) if T24_LINEA in t)
        i02 = max(i for i, t in enumerate(txt[:i24]) if T02_LINEA in t)
        dt_ms = _ms(txt[i24]) - _ms(txt[i02])
        med_tras = [t for t in txt[i24:] if "nodo: med: " in t]
        i_dns = next((i for i, t in enumerate(txt[i24:], i24) if DNS_DETENIDO in t), None)
        dns_ms = None if i_dns is None else _ms(txt[i_dns]) - _ms(txt[i24])
        nvs = [t for t in txt if "nvs: config escrita" in t]
        sin_dns = [t for t in txt if DNS_NO_DISPONIBLE in t]
        rein = [k for k in reinicios(ent) if k > i02]
        c.note(f"- T02 → T24 en el reloj del DUT: {dt_ms} ms (esperado {PORTAL_MS} ± {TOL_MS})",
               f"- `{DNS_DETENIDO}` (E14): " + ("ausente" if dns_ms is None else f"a {dns_ms} ms de T24"),
               f"- escaneos tras el cierre: {['visible' if v else 'no' for v in tras]}",
               f"- líneas med: después del cierre: {len(med_tras)}; `nvs: config escrita`: {len(nvs)}; "
               f"reinicios tras T02: {len(rein)}")
        assert abs(dt_ms - PORTAL_MS) <= TOL_MS, f"T24 a {dt_ms} ms de T02"
        assert not any(tras), "el AP del portal sigue visible tras T24"
        assert dns_ms is not None and 0 <= dns_ms <= DNS_MAX_MS, f"el DNS no se detuvo en {DNS_MAX_MS} ms (E14): {dns_ms}"
        assert med_tras, "la medición no siguió en ESPERA"
        assert not nvs, "se escribió la NVS"
        assert not sin_dns, f"el DNS no se pudo ligar en T02 (E14): {sin_dns[:1]}"
        assert not rein, "el DUT se reinició tras T02"

        c.step("Otro reset: el portal vuelve a abrirse")
        t1 = time.time()
        tb.serial_reset(dut_slot)
        assert reg.esperar(re.escape(T02_LINEA), 60, desde_ts=t1), "sin T02 tras el segundo reset"
        time.sleep(5)
        otra = any(_visible(tb, nodo) for _ in range(3))
        c.save_log("serie", [e.get("text", "") for e in reg.leer()])
        c.note(f"- tras el segundo reset, `{nodo}` visible: {'sí' if otra else 'no'}")
        assert otra, "el portal no se reabre tras un reset"
        c.passed(f"T24 a {dt_ms / 1000:.1f} s de T02; dns detenido a {dns_ms} ms; AP fuera en los {ESCANEOS_TRAS} escaneos; "
                 f"{len(med_tras)} med: en ESPERA; sin NVS ni reinicio; reabierto tras un reset")
