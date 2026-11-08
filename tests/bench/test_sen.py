"""TC-SEN-* — driver SHT41 (FSD §8), nivel target observado por el banco.
Atómico: graba la imagen de la CI del commit bajo prueba (sin tocar la NVS: el
ciclo corre en cualquier estado, FR-MED-02) y observa su log serie."""
import re
import time
import pytest

from benchlib import _after_last_reset, _lines, _parse_flash_args, case

CICLOS = 3
CICLO_S = 60
MED = re.compile(r"med: T=(-?\d+\.\d) HR=(\d+\.\d) Td=(-?\d+\.\d|-)")


def _distintas(vistas):
    """Líneas med: distintas: el buffer del banco puede repetir una línea (misma
    marca de tiempo del DUT, «I (508)»); se cuenta una vez por texto."""
    vistas_texto, out = set(), []
    for e in vistas:
        t = e.get("text", "").strip()
        if "med: " in t and t not in vistas_texto:
            vistas_texto.add(t)
            out.append(e)
    return out


def test_tc_sen_03_three_cycles(testbench, dut_slot, firmware, run_dir):
    """TC-SEN-03 · FR-SEN-01 (target) — 3 ciclos con el sensor conectado: 3 líneas med: con T ∈ [0, 50] °C."""
    tb = testbench
    with case(tb, "TC-SEN-03", "Tres ciclos de medición con el SHT41", run_dir,
              spec="TC-SEN villa-nodo-clima-piloto") as c:
        c.note(f"- imagen: `{firmware['version']}` (variante {firmware['variant']}, run CI {firmware['ci_run']})", "")
        c.step(f"Precondiciones: grabar la imagen de la CI en {dut_slot} (NVS intacta)")
        images = _parse_flash_args(firmware["dir"] / "coldflash")
        res = tb.flash(dut_slot, images, chip="esp32s3")
        assert res.get("ok") and res.get("returncode", 0) == 0, f"flash falló: {res.get('error') or res}"

        c.step(f"Reset y observación de {CICLOS} ciclos ({CICLOS} × {CICLO_S} s)")
        t0 = time.time()
        reset_out = tb.serial_reset(dut_slot)
        fin = t0 + (CICLOS - 1) * CICLO_S + 30
        vistas = []
        while time.time() < fin:
            out = tb.serial_output(dut_slot, lines=500, since=t0)
            vistas = [e if isinstance(e, dict) else {"text": str(e), "ts": 0} for e in (out.get("lines") or [])]
            if len(_distintas(vistas)) >= CICLOS:
                break
            time.sleep(2)
        lines = _lines(reset_out) + ["--- buffer del slot ---"] + [e.get("text", "") for e in vistas]
        c.save_log("serie", lines)

        boot = _after_last_reset(_lines(reset_out))
        fw = next((ln for ln in boot + lines if "boot: " in ln and " fw=" in ln), "")
        meds = _distintas(vistas)
        c.note("", "## Resultado", "", f"- arranque: `{fw.strip()}`",
               *[f"- ts {e.get('ts', 0) - t0:+.1f} s: `{e['text'].strip()}`" for e in meds])
        if len(meds) >= 2:
            dts = [round(b.get("ts", 0) - a.get("ts", 0), 1) for a, b in zip(meds, meds[1:])]
            c.note(f"- intervalos entre líneas med: {dts} s (informativo; FR-MED-01 es de la Fase 2)")
        assert firmware["version"] in fw, f"el arranque no es la imagen {firmware['version']}: «{fw.strip()}»"
        invalidas = [e["text"] for e in meds if "med: invalida" in e["text"]]
        assert not invalidas, f"lecturas inválidas: {invalidas}"
        assert len(meds) >= CICLOS, f"{len(meds)} líneas med: en {fin - t0:.0f} s; se esperaban {CICLOS}"
        for e in meds[:CICLOS]:
            m = MED.search(e["text"])
            assert m, f"línea med: sin el formato de E3: «{e['text'].strip()}»"
            t = float(m.group(1))
            assert 0.0 <= t <= 50.0, f"T = {t} °C fuera de [0, 50]"
        c.passed(f"{CICLOS} líneas med: válidas con T en [0, 50] °C")


# ---------------------------------------------------------------------------
# TC-SEN-04 · FR-SEN-03 (bench, Fase 2): SDA desconectado 3 ciclos por el operador
# (sda-disconnect: no hay conmutador) y reconectado; observado por MQTT y por la consola.

SEN03_INVALIDOS = 3            # ciclos con SDA suelto
SEN03_ESPERA_OPERADOR_S = 300  # sda-disconnect: con 180 s un aviso caducó (2026-11-01)
SEN03_LIMITE_S = 61            # timing del contrato, desde la reconexión
SEN03_TOLERANCIA_S = 60        # tolerancia: un ciclo
SEN03_PROHIBIDOS = (0.0, -45.0, -6.0)
AVISO_SDA_OFF = ("TC-SEN-04 (FR-SEN-03): desconecta el Dupont de SDA del SHT41 en la protoboard "
                 "y pulsa «Hecho». NO lo vuelvas a conectar todavía: en unos 3 minutos saldrá otro aviso.")
AVISO_SDA_ON = ("TC-SEN-04 (FR-SEN-03): vuelve a conectar el Dupont de SDA del SHT41 y pulsa «Hecho» "
                "en cuanto esté conectado.")


def _status_vivos(msgs, base, desde=0.0, hasta=float("inf")):
    import json
    out = []
    for m in msgs:
        if m["topic"] == f"{base}/status" and not m["retain"] and m["payload"] and desde <= m["t"] <= hasta:
            try:
                st = json.loads(m["payload"])
            except ValueError:
                continue
            if st.get("estado") == "online":
                out.append((m["t"], st))
    return out


def _medidas_vivas(msgs, base, desde=0.0, hasta=float("inf")):
    from test_mqtt import MEDIDAS
    return [m for m in msgs if m["topic"].rsplit("/", 1)[-1] in MEDIDAS and m["topic"].startswith(base + "/")
            and not m["retain"] and m["payload"] and desde <= m["t"] <= hasta]


def test_tc_sen_04_sda_disconnect_recovery(testbench, dut_slot, dut_mac, firmware, run_dir, tmp_path):
    """TC-SEN-04 · FR-SEN-03 — OPERATIVO con medidas válidas; el operador desconecta SDA durante
    3 ciclos y lo reconecta. Durante la desconexión no llega ninguna medida (ni 0, −45, −6, NaN
    ni el último valor), err_sensor sube 3 (± 1); tras reconectar llegan las tres medidas válidas
    en ≤ 61 s (tolerancia un ciclo), sin reinicio (uptime creciente, mismo reset, sin boot: nuevo)."""
    import json
    from test_mqtt import MEDIDAS, _a_operativo, _nodo, _suscribir, configurado
    tb = testbench
    nodo = _nodo(dut_mac)
    base = f"sitio1/zona1/{nodo}"
    with case(tb, "TC-SEN-04", "Recuperación tras desconectar SDA", run_dir,
              spec="TC-SEN villa-nodo-clima-piloto") as c, \
            configurado(tb, dut_slot, dut_mac, firmware, c, tmp_path) as banco:
        banco.broker_on()
        with _suscribir(tb, nodo) as sub:
            t0, reg = _a_operativo(tb, dut_slot, banco, c)
            c.step("Precondición: dos status en vivo con medidas válidas")
            fin = time.time() + 150
            while time.time() < fin and len(_status_vivos(sub.mensajes(), base, t0)) < 2:
                time.sleep(1)
            time.sleep(3)
            assert _medidas_vivas(sub.mensajes(), base, t0), "precondición: ninguna medida válida antes del corte"

            c.step("Aviso: desconectar SDA")
            t_aviso_off = time.time()
            ok_off = tb.human_interaction(AVISO_SDA_OFF, timeout=SEN03_ESPERA_OPERADOR_S)
            t_off = time.time()
            if not ok_off:
                pytest.skip("not done: el operador no confirmó la desconexión de SDA")
            antes = _status_vivos(sub.mensajes(), base, t0, t_aviso_off)
            err0 = antes[-1][1]["err_sensor"]
            c.step(f"Esperar {SEN03_INVALIDOS} ciclos con lectura inválida (status con err_sensor creciente)")
            fin = time.time() + SEN03_INVALIDOS * 60 + 30
            while time.time() < fin:
                st = _status_vivos(sub.mensajes(), base, t_off)
                if st and st[-1][1]["err_sensor"] - err0 >= SEN03_INVALIDOS:
                    break
                time.sleep(1)

            c.step("Aviso: reconectar SDA")
            t_aviso_on = time.time()
            ok_on = tb.human_interaction(AVISO_SDA_ON, timeout=SEN03_ESPERA_OPERADOR_S)
            t_on = time.time()
            if not ok_on:
                pytest.skip("not done: el operador no confirmó la reconexión de SDA (déjalo conectado)")
            c.step("Esperar las medidas del primer ciclo tras reconectar y un status más")
            fin = t_on + SEN03_LIMITE_S + SEN03_TOLERANCIA_S + 15
            while time.time() < fin:
                meds = _medidas_vivas(sub.mensajes(), base, t_aviso_on)
                if {m["topic"].rsplit("/", 1)[-1] for m in meds} >= set(MEDIDAS):
                    break
                time.sleep(1)
            time.sleep(5)
            msgs = sub.mensajes()
        ent = reg.leer()
        c.save_log("serie", [e["text"] for e in ent])
        c.save_log("mqtt", [f"{m['t'] - t0:+.2f} s retain={int(m['retain'])} qos={m['qos']} {m['topic']} {m['payload']}"
                            for m in msgs])

        st_antes = _status_vivos(msgs, base, t0, t_aviso_off)
        st_desc = _status_vivos(msgs, base, t_off, t_aviso_on)
        st_desp = _status_vivos(msgs, base, t_on)
        meds_desc = _medidas_vivas(msgs, base, t_off, t_aviso_on)
        meds_ambig = _medidas_vivas(msgs, base, t_aviso_on, t_on)
        meds_desp = _medidas_vivas(msgs, base, t_on)
        prim = {}
        for m in meds_ambig + meds_desp:
            prim.setdefault(m["topic"].rsplit("/", 1)[-1], m)
        t_rec = (max(m["t"] for m in prim.values()) - t_on) if len(prim) == len(MEDIDAS) else None
        invalidas = [e["text"].strip() for e in ent if "med: invalida" in e["text"]]
        boots = [e["text"].strip() for e in ent if "boot: " in e["text"] and " fw=" in e["text"]]
        a = st_antes[-1][1]
        d = st_desp[-1][1] if st_desp else None
        derr = (st_desc[-1][1]["err_sensor"] - a["err_sensor"]) if st_desc else None
        c.note("", "## Resultado", "",
               f"- operador: desconexión confirmada a {t_off - t_aviso_off:.1f} s del aviso; reconexión a "
               f"{t_on - t_aviso_on:.1f} s del aviso; SDA suelto ≈ {t_aviso_on - t_off:.0f} s",
               f"- último status antes: uptime_s={a['uptime_s']}, lecturas={a['lecturas']}, "
               f"err_sensor={a['err_sensor']}, reset={a['reset']}",
               f"- status con SDA suelto: {len(st_desc)}; err_sensor "
               f"{[s['err_sensor'] for _, s in st_desc]} (Δ = {derr})",
               f"- medidas en vivo con SDA suelto: {len(meds_desc)}"
               + "".join(f"; `{m['topic'].replace(base, '<base>')}` {m['payload']}" for m in meds_desc),
               f"- líneas «med: invalida» en la consola: {len(invalidas)}" + (f" ({invalidas[0]} …)" if invalidas else ""),
               "- primeras medidas tras reconectar: " + ", ".join(
                   f"{k}={prim[k]['payload']} a {prim[k]['t'] - t_on:+.1f} s" for k in MEDIDAS if k in prim),
               f"- status tras reconectar: " + (f"uptime_s={d['uptime_s']}, lecturas={d['lecturas']}, "
                                               f"err_sensor={d['err_sensor']}, reset={d['reset']}" if d else "ninguno"),
               f"- arranques en la consola: {len(boots)}")
        assert not meds_desc, f"{len(meds_desc)} medidas publicadas con SDA suelto: {[m['payload'] for m in meds_desc]}"
        for m in meds_ambig + meds_desp:
            v = json.loads(m["payload"]).get("v")
            assert isinstance(v, (int, float)) and v == v and v not in SEN03_PROHIBIDOS, f"valor prohibido: {m['payload']}"
        assert derr is not None and abs(derr - SEN03_INVALIDOS) <= 1, f"Δerr_sensor={derr}, esperado {SEN03_INVALIDOS} ± 1"
        assert len(prim) == len(MEDIDAS), f"tras reconectar solo llegaron {sorted(prim)}"
        assert t_rec <= SEN03_LIMITE_S + SEN03_TOLERANCIA_S, f"medidas a {t_rec:.1f} s de reconectar (> 61 s + un ciclo)"
        assert d and d["uptime_s"] > a["uptime_s"] and d["reset"] == a["reset"], "el nodo se reinició (uptime/reset)"
        assert len(boots) <= 1, f"el nodo se reinició: {boots}"
        c.passed(f"0 medidas con SDA suelto, Δerr_sensor={derr}, tres medidas válidas a {t_rec:.1f} s de "
                 f"reconectar (≤ {SEN03_LIMITE_S} s{'' if t_rec <= SEN03_LIMITE_S else ', dentro de la tolerancia'}); sin reinicio")
