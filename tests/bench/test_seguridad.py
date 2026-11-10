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
