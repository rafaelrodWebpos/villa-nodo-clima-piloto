"""Diagnóstico de un corte de alimentación (TC-CFG-02): estado del slot, buffer serie y
log de actividad del banco a 1 Hz, antes y después del corte del operador."""
import json, os, re, threading, time
from testbench_driver import TestbenchDriver
tb = TestbenchDriver(os.environ["TESTBENCH_URL"])
SLOT = "SLOT1"
MAC = re.compile(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")
UP = re.compile(r"^\w \((\d+)\)")
out = open("/sp/diag_corte.jsonl", "w")
t0 = time.time(); fase = {"v": "antes"}; parar = threading.Event()
def log(**k):
    k["t"] = round(time.time() - t0, 1); k["fase"] = fase["v"]
    out.write(MAC.sub("<mac>", json.dumps(k, ensure_ascii=False)) + "\n"); out.flush()
CAMPOS = ("present", "running", "pid", "devnode", "devnodes", "state", "flapping", "recovering",
          "recover_retries", "last_action", "last_event_ts", "last_error", "usb_devices")
def muestreo():
    prev = None
    while not parar.is_set():
        try:
            s = tb.get_slot(SLOT); est = {k: s.get(k) for k in CAMPOS}
            b = (tb.serial_output(SLOT, lines=1, since=0).get("lines") or [{}])[-1]
            m = UP.match(b.get("text", "")); ult = (round(b.get("ts", 0) - t0, 1), int(m.group(1)) // 1000 if m else None, b.get("text", "")[:70])
            if (est, ult) != prev: log(slot=est, ultima=ult); prev = (est, ult)
        except Exception as e:
            log(error=repr(e)[:200])
        time.sleep(1)
th = threading.Thread(target=muestreo, daemon=True); th.start()
time.sleep(10)
fase["v"] = "aviso"; log(evento="aviso mostrado")
ok = tb.human_interaction("Diagnóstico de TC-CFG-02 (un solo corte): desenchufa el cable USB-C de la placa, "
                          "espera 5 segundos y vuelve a enchufarlo en el mismo puerto de la Pi. Después pulsa «Hecho».",
                          timeout=600)
fase["v"] = "tras_hecho"; t_hecho = time.time(); log(evento="hecho" if ok else "cancelado o agotado")
probado = False
while ok and time.time() - t_hecho < 240:
    if not probado and time.time() - t_hecho > 45:
        lin = tb.serial_output(SLOT, lines=500, since=t_hecho - 600).get("lines") or []
        boots = [e["text"] for e in lin if "boot: " in e.get("text", "") and " fw=" in e.get("text", "") and e.get("ts", 0) > t0]
        log(evento="comprobación +45 s", boots_en_buffer=boots[-2:], lineas=len(lin))
        if not boots:
            r = tb.serial_monitor(SLOT, pattern="nodo: ", timeout=15)
            log(evento="serial_monitor tras +45 s", ok=r.get("ok"), matched=r.get("matched"),
                line=(r.get("line") or "")[:100], n_output=len(r.get("output") or []),
                output_tail=[(o.get("text", o) if isinstance(o, dict) else str(o))[:90] for o in (r.get("output") or [])][-6:])
        probado = True
    time.sleep(2)
parar.set(); th.join(5)
try:
    L = tb._api_get("/api/log", timeout=10)
    E = L.get("entries", L) if isinstance(L, dict) else L
    log(evento="log de actividad", entradas=[e for e in E if isinstance(e, dict)][-30:])
except Exception as e:
    log(error="api/log " + repr(e)[:150])
lin = tb.serial_output(SLOT, lines=600, since=t0 - 5).get("lines") or []
log(evento="buffer final", lineas=[(round(e.get("ts", 0) - t0, 1), e.get("text", "")[:100]) for e in lin
                                   if any(k in e.get("text", "") for k in ("rst:", "boot: clima", " fw=", "con: ARRANQUE", "cfg:", "ESP-ROM"))])
log(evento="fin")
