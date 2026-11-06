"""¿Qué causa de reinicio da cada reset del banco? (A) /api/serial/reset; (B) pulso en EN por /api/gpio/set."""
import json, os, re, time
from testbench_driver import TestbenchDriver
tb = TestbenchDriver(os.environ["TESTBENCH_URL"]); SLOT = "SLOT1"
MAC = re.compile(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")
def clave(lineas):
    return [MAC.sub("<mac>", l)[:120] for l in lineas if l.startswith("rst:") or ("boot: " in l and " fw=" in l)]
res = {}
s = tb.get_slot(SLOT); res["slot"] = {k: s.get(k) for k in ("gpio_en", "gpio_boot", "has_gpio", "gpio_wired", "gpio_wired_detail")}
try: res["gpio_antes"] = tb.gpio_get()
except Exception as e: res["gpio_antes"] = repr(e)[:150]
# (A) reset del banco por API
r = tb.serial_reset(SLOT)
out = r.get("output") or []
res["A_serial_reset"] = {"method": r.get("method", "serial (DTR/RTS)"), "lineas": clave([o.get("text", "") if isinstance(o, dict) else str(o) for o in out])}
time.sleep(8)
# (B) pulso en EN por la GPIO del slot
en = s.get("gpio_en"); t0 = time.time()
res["B_set_bajo"] = tb.gpio_set(en, 0); time.sleep(0.3); res["B_set_libre"] = tb.gpio_set(en, "z")
time.sleep(6)
lin = [e.get("text", "") for e in (tb.serial_output(SLOT, lines=300, since=t0 - 1).get("lines") or [])]
res["B_pulso_en"] = {"lineas": clave(lin), "n_lineas_tras_pulso": len(lin)}
try: res["gpio_despues"] = tb.gpio_get()
except Exception as e: res["gpio_despues"] = repr(e)[:150]
print(MAC.sub("<mac>", json.dumps(res, ensure_ascii=False, indent=1)))
