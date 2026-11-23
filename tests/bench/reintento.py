"""Reintento de las llamadas al banco ante cortes breves de la red de la laptop (2026-11-21).

WSL, en modo de red `mirrored`, pierde a ratos la ruta hacia la LAN («connect() failed: 101» en
dmesg). Una llamada al banco que cae en ese momento falla con «Network is unreachable», aunque el
banco esté bien. El 2026-11-21 eso tumbó TC-LOG-08 y dejó su AP encendido, y en la 24 h de AGUA
dio «Connection reset by peer» (upstream #89).

`instalar()` hace que TestbenchDriver reintente durante REINTENTO_S, cada ESPERA_S, solo cuando es
seguro:
- errores de conexión en los que la petición no salió de la laptop o el banco no la aceptó
  (ENETUNREACH 101, EHOSTUNREACH 113, ECONNREFUSED 111), en cualquier método;
- un corte a mitad de la respuesta (ConnectionResetError, RemoteDisconnected), solo en GET: un
  POST pudo haberse ejecutado ya en el banco (grabar, resetear, levantar el AP) y no se repite.
Nunca se reintenta una respuesta HTTP con error (HTTPError): esa es la respuesta del banco.

Solo biblioteca estándar: lo prueba tests/host/test_reintento.py en la CI.
"""
import errno
import http.client
import sys
import time
import types
import urllib.error
import urllib.request

REINTENTO_S = 60
ESPERA_S = 5
SIN_RUTA = {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ECONNREFUSED}


def _metodo(req):
    return req.get_method() if isinstance(req, urllib.request.Request) else "GET"


def reintentable(exc, metodo):
    """¿Se puede repetir sin riesgo la petición que falló con exc?"""
    if isinstance(exc, urllib.error.HTTPError):
        return False
    razon = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(razon, OSError) and razon.errno in SIN_RUTA:
        return True
    return metodo == "GET" and isinstance(razon, (ConnectionResetError, http.client.RemoteDisconnected))


def con_reintento(abrir, reintento_s=REINTENTO_S, espera_s=ESPERA_S, dormir=time.sleep, reloj=time.monotonic):
    """Envuelve una función con la firma de urllib.request.urlopen."""
    def urlopen(req, *a, **k):
        limite = reloj() + reintento_s
        intento = 0
        while True:
            intento += 1
            try:
                return abrir(req, *a, **k)
            except (urllib.error.URLError, ConnectionResetError, http.client.RemoteDisconnected) as e:
                if not reintentable(e, _metodo(req)) or reloj() + espera_s > limite:
                    raise
                url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
                print(f"[reintento] {_metodo(req)} {url.split('?')[0]} intento {intento}: "
                      f"{type(e).__name__}: {e}; nuevo intento en {espera_s} s", file=sys.stderr)
                dormir(espera_s)
    return urlopen


def instalar(modulo_driver):
    """Hace que el módulo del driver use urlopen con reintento, sin tocar urllib para nadie más."""
    request = types.ModuleType("urllib.request")
    request.__dict__.update(urllib.request.__dict__)
    request.urlopen = con_reintento(urllib.request.urlopen)
    shim = types.ModuleType("urllib")
    shim.request, shim.error = request, urllib.error
    shim.parse = getattr(urllib, "parse", None) or __import__("urllib.parse").parse
    modulo_driver.urllib = shim
    return modulo_driver
