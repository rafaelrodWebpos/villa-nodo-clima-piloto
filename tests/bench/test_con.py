"""TC-CON-* — gestor de conectividad (FSD §6), nivel bench. Atómicos: cada uno
establece su precondición con los procedimientos de benchlib."""
import re
import time

from benchlib import _parse_flash_args, aprovisionar, case, esperar_lineas, primera

BACKOFF_S = [1, 2, 4, 8, 16, 32, 60, 60, 60, 60]   # FR-CON-02
TOLERANCIA = 0.10
CAIDA = "-> CONECTANDO_WIFI (wifi_down)"


def _ms(texto):
    m = re.match(r"\s*\w \((\d+)\)", texto)
    return int(m.group(1)) if m else None


def _unicas(vistas):
    """Una vez por línea (el buffer del banco puede repetirlas; la marca «I (ms)» del DUT las distingue)."""
    vistas_t, out = set(), []
    for e in vistas:
        t = e.get("text", "").strip()
        if t and t not in vistas_t:
            vistas_t.add(t)
            out.append(e)
    return out


def test_tc_con_03_wifi_backoff(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-03 · FR-CON-02 (fila Wi-Fi), T09, T10 — AP apagado desde el arranque: 10 intervalos del backoff."""
    tb = testbench
    ssid_portal = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "TC-CON-03", "Backoff de Wi-Fi con el AP apagado", run_dir, spec="TC-CON villa-nodo-clima-piloto") as c:
        # Atómico: graba él mismo la imagen de la CI del commit bajo prueba (no depende del orden)
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot}")
        res = tb.flash(dut_slot, _parse_flash_args(firmware["dir"] / "coldflash"), chip="esp32s3")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"
        aprovisionar(tb, dut_slot, ssid_portal, c, tmp_path)
        assert not tb.ap_status().get("active"), "el AP del banco sigue activo"
        c.step("Reset con el AP del banco apagado; observación de 10 reintentos (≈ 6 min)")
        t0 = time.time()
        tb.serial_reset(dut_slot)
        vistas = esperar_lineas(tb, dut_slot, t0, ["wifi: intento 11"], timeout=sum(BACKOFF_S) + 120)
        lineas = _unicas(vistas)
        c.save_log("serie", [c._r(e["text"]) for e in lineas])

        textos = [e["text"] for e in lineas]
        assert primera(lineas, "con: ARRANQUE -> CONECTANDO_WIFI (fin_arranque)"), "falta T01"
        assert not any("con: ARRANQUE -> PORTAL" in t for t in textos), "el nodo configurado abrió el portal"
        assert not any("softAP" in t for t in textos if "wifi:mode" in t), "se abrió el AP (prohibido en T09/T10)"
        boots = [t for t in textos if "boot: " in t and " fw=" in t]
        assert boots and firmware["version"] in boots[0], f"el arranque no es la imagen {firmware['version']}"
        assert len(boots) <= 1, "el nodo se reinició durante los reintentos"
        # Cada intervalo: de la línea de T09 al siguiente «wifi: intento <n>», en el reloj del DUT
        intervalos, i = [], 0
        while i < len(textos) and len(intervalos) < len(BACKOFF_S):
            if CAIDA in textos[i]:
                desde = _ms(textos[i])
                sig = next((t for t in textos[i + 1:] if "wifi: intento " in t), None)
                if sig is None:
                    break
                intervalos.append(round((_ms(sig) - desde) / 1000, 2))
            i += 1
        t09 = sum("con: CONECTANDO_WIFI -> CONECTANDO_WIFI (wifi_down)" in t for t in textos)
        t10 = sum("con: CONECTANDO_WIFI -> CONECTANDO_WIFI (backoff)" in t for t in textos)
        c.note("", "## Resultado", "", f"- líneas T09: {t09}, T10: {t10}",
               *[f"- intervalo {k + 1}: {v} s (esperado {BACKOFF_S[k]} s ± 10 %)" for k, v in enumerate(intervalos)])
        assert len(intervalos) == len(BACKOFF_S), f"solo {len(intervalos)} intervalos medidos"
        for k, (v, e) in enumerate(zip(intervalos, BACKOFF_S)):
            assert v >= 0.9, f"intervalo {k + 1} en ráfaga: {v} s"   # ráfaga: < 1 s (−10 %)
            assert abs(v - e) <= e * TOLERANCIA, f"intervalo {k + 1}: {v} s fuera de {e} s ± 10 %"
        c.passed(f"10 intervalos del backoff dentro de ±10 %: {intervalos}")


VENTANA_CON06_S = 15 * 60    # FR-CON-06: 15 min
ESCANEOS_CON06 = 5           # escaneos repartidos en la ventana


def test_tc_con_06_never_portal(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-CON-06 · FR-CON-06 — configurado y con el AP apagado desde el arranque (Fase 1): en 15 min
    ninguna línea con: con destino distinto de CONECTANDO_WIFI y el AP del portal no aparece."""
    tb = testbench
    ssid_portal = "clima-" + dut_mac.replace(":", "").lower()[-6:]
    with case(tb, "TC-CON-06", "Nunca vuelve al portal sin Wi-Fi", run_dir, spec="TC-CON villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot}")
        res = tb.flash(dut_slot, _parse_flash_args(firmware["dir"] / "coldflash"), chip="esp32s3")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"
        aprovisionar(tb, dut_slot, ssid_portal, c, tmp_path)
        assert not tb.ap_status().get("active"), "el AP del banco sigue activo"
        c.step(f"Reset con el AP del banco apagado; {VENTANA_CON06_S // 60} min de observación y {ESCANEOS_CON06} escaneos")
        t0 = time.time()
        tb.serial_reset(dut_slot)
        vistos = []
        for k in range(ESCANEOS_CON06):
            objetivo = t0 + (k + 1) * VENTANA_CON06_S / ESCANEOS_CON06
            time.sleep(max(0.0, objetivo - time.time()))
            nets = tb.scan().get("networks") or []
            clima = sorted({n.get("ssid") for n in nets if str(n.get("ssid", "")).startswith("clima-")})
            vistos.append((round(time.time() - t0), clima))
        lineas = _unicas(esperar_lineas(tb, dut_slot, t0, [], timeout=0))
        ult = max((i for i, e in enumerate(lineas) if e["text"].startswith("rst:")), default=0)
        lineas = lineas[ult:]                     # solo nuestro arranque (el buffer entrega tarde la cola del anterior)
        c.save_log("serie", [c._r(e["text"]) for e in lineas])
        cons = [e["text"].strip() for e in lineas if " con: " in e["text"]]
        otros = [t for t in cons if not t.split(" -> ", 1)[-1].startswith("CONECTANDO_WIFI")]
        ultimo = _ms(lineas[-1]["text"]) if lineas and _ms(lineas[-1]["text"]) else 0
        c.note("", "## Resultado", "", f"- líneas con: {len(cons)} (destino distinto de CONECTANDO_WIFI: {len(otros)})",
               f"- última línea del DUT a los {ultimo / 1000:.0f} s de su arranque",
               *[f"- escaneo a t={t} s: {v or 'ningún clima-*'}" for t, v in vistos])
        assert cons and "con: ARRANQUE -> CONECTANDO_WIFI (fin_arranque)" in cons[0], "el arranque no fue T01"
        assert not otros, f"líneas con: hacia otro estado: {otros[:3]}"
        assert all(ssid_portal not in v for _, v in vistos), "el AP del portal apareció en el escaneo"
        assert ultimo >= (VENTANA_CON06_S - 60) * 1000, f"el log del DUT cubre solo {ultimo / 1000:.0f} s de la ventana"
        assert sum("boot: " in e["text"] for e in lineas) <= 1, "el nodo se reinició en la ventana"
        c.passed(f"{len(cons)} líneas con:, todas hacia CONECTANDO_WIFI; el AP del portal no apareció en {ESCANEOS_CON06} escaneos")
