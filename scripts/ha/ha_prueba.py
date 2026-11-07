#!/usr/bin/env python3
"""Home Assistant de prueba para JRN-01.5 y FR-HA-* (capacidad home-assistant-test).

Decisión H-52 del propietario (2026-11-07): corre en la laptop, en el Docker de WSL,
y llega al broker del banco por la LAN; en el Pi del banco no se instala nada.

    python3 scripts/ha/ha_prueba.py up     # instancia nueva, sin estado, con onboarding hecho
    python3 scripts/ha/ha_prueba.py down   # la borra con su configuración

`up` arranca una imagen fija (HA_IMAGEN) con su /config en un directorio temporal
nuevo, crea un usuario de usar y tirar y escribe en `.ha-prueba.env` (ignorado por
git, como todo *.env) HA_URL, HA_CLIENT_ID y HA_REFRESH_TOKEN. Los tests piden con
ellos un token de acceso y añaden la integración MQTT apuntando al broker del banco
cuando lo tienen arrancado (el asistente de la integración comprueba la conexión).
Nada de esto se versiona: ni la dirección del banco ni las credenciales.
Solo usa la biblioteca estándar.
"""
import json
import pathlib
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HA_IMAGEN = "homeassistant/home-assistant:2026.10.4"   # estable, publicada el 2026-10-24
NOMBRE = "ha-prueba"
PUERTO = 8123
URL = f"http://127.0.0.1:{PUERTO}"
REPO = pathlib.Path(__file__).resolve().parents[2]
ENV = REPO / ".ha-prueba.env"
CLIENT_ID = f"{URL}/"


def _http(metodo, ruta, datos=None, token=None, form=False, timeout=15):
    cab = {}
    cuerpo = None
    if datos is not None:
        if form:
            cuerpo = urllib.parse.urlencode(datos).encode()
            cab["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            cuerpo = json.dumps(datos).encode()
            cab["Content-Type"] = "application/json"
    if token:
        cab["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(URL + ruta, data=cuerpo, headers=cab, method=metodo)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        txt = r.read().decode()
        return json.loads(txt) if txt else {}


def _docker(*args, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def _directorio():
    r = _docker("inspect", NOMBRE, "--format", "{{range .Mounts}}{{if eq .Destination \"/config\"}}{{.Source}}{{end}}{{end}}",
                check=False)
    return r.stdout.strip() if r.returncode == 0 else ""


def down():
    d = _directorio()
    _docker("rm", "-f", NOMBRE, check=False)
    if d and pathlib.Path(d).name.startswith("ha-prueba-"):
        # /config lo escribe root dentro del contenedor: se borra desde otro contenedor
        _docker("run", "--rm", "-v", f"{d}:/c", "--entrypoint", "sh", HA_IMAGEN, "-c", "rm -rf /c/* /c/.[!.]*",
                check=False)
        shutil.rmtree(d, ignore_errors=True)
    ENV.unlink(missing_ok=True)
    print("ha-prueba: borrado")


def up():
    down()
    d = tempfile.mkdtemp(prefix="ha-prueba-")
    _docker("run", "-d", "--name", NOMBRE, "-p", f"127.0.0.1:{PUERTO}:{PUERTO}", "-e", "TZ=UTC",
            "-v", f"{d}:/config", HA_IMAGEN)
    fin = time.time() + 300
    while True:
        try:
            pasos = _http("GET", "/api/onboarding")
            break
        except (urllib.error.URLError, ConnectionError, OSError):
            if time.time() > fin:
                sys.exit("ha-prueba: Home Assistant no respondió en 300 s")
            time.sleep(3)
    hechos = {p["step"] for p in pasos if p.get("done")}
    assert "user" not in hechos, "instancia nueva con usuario ya creado"
    clave = secrets.token_urlsafe(24)
    code = _http("POST", "/api/onboarding/users",
                 {"client_id": CLIENT_ID, "name": "Banco", "username": "banco", "password": clave,
                  "language": "es"})["auth_code"]
    tok = _http("POST", "/auth/token", {"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
                form=True)
    acceso = tok["access_token"]
    for paso, datos in (("core_config", {}), ("analytics", {}),
                        ("integration", {"client_id": CLIENT_ID, "redirect_uri": f"{URL}/?auth_callback=1"})):
        try:
            _http("POST", f"/api/onboarding/{paso}", datos, token=acceso)
        except urllib.error.HTTPError as e:
            if e.code != 403:      # 403: paso ya hecho
                raise
    ver = _http("GET", "/api/config", token=acceso).get("version")
    ENV.write_text(f"HA_URL={URL}\nHA_CLIENT_ID={CLIENT_ID}\nHA_REFRESH_TOKEN={tok['refresh_token']}\n")
    print(f"ha-prueba: Home Assistant {ver} listo en {URL}; credenciales en {ENV.name} (no versionado)")


if __name__ == "__main__":
    {"up": up, "down": down}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
