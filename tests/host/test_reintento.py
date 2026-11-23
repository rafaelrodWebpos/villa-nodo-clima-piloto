"""Nivel host de tests/bench/reintento.py (2026-11-21): qué se reintenta y qué no.
Corre con `python3 tests/host/test_reintento.py` (sin dependencias)."""
import errno
import http.client
import pathlib
import sys
import types
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))
import reintento  # noqa: E402


def falla_n(n, exc):
    """urlopen simulado: falla n veces con exc y luego responde."""
    estado = {"llamadas": 0}

    def abrir(req, *a, **k):
        estado["llamadas"] += 1
        if estado["llamadas"] <= n:
            raise exc
        return "ok"
    return abrir, estado


class Reloj:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


def envolver(abrir, reloj):
    return reintento.con_reintento(abrir, reintento_s=60, espera_s=5, dormir=reloj.dormir, reloj=reloj)


GET = urllib.request.Request("http://banco.invalid/api/wifi/ap_status")
POST = urllib.request.Request("http://banco.invalid/api/serial/reset", data=b"{}", method="POST")
SIN_RED = urllib.error.URLError(OSError(errno.ENETUNREACH, "Network is unreachable"))


class TestReintento(unittest.TestCase):
    def test_sin_red_se_reintenta_hasta_que_vuelve(self):
        r = Reloj()
        abrir, e = falla_n(3, SIN_RED)
        self.assertEqual(envolver(abrir, r)(POST), "ok")      # ni siquiera salió: seguro también en POST
        self.assertEqual(e["llamadas"], 4)
        self.assertEqual(r.t, 15)

    def test_sin_red_mas_de_un_minuto_falla(self):
        r = Reloj()
        abrir, e = falla_n(99, SIN_RED)
        with self.assertRaises(urllib.error.URLError):
            envolver(abrir, r)(GET)
        self.assertLessEqual(r.t, 60)

    def test_rechazo_y_sin_ruta_al_host(self):
        for n in (errno.ECONNREFUSED, errno.EHOSTUNREACH):
            abrir, _ = falla_n(1, urllib.error.URLError(OSError(n, "x")))
            self.assertEqual(envolver(abrir, Reloj())(POST), "ok")

    def test_corte_a_mitad_solo_en_get(self):
        for exc in (ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"),
                    http.client.RemoteDisconnected("Remote end closed connection without response"),
                    urllib.error.URLError(ConnectionResetError(errno.ECONNRESET, "reset"))):
            abrir, _ = falla_n(1, exc)
            self.assertEqual(envolver(abrir, Reloj())(GET), "ok")
            abrir, e = falla_n(1, exc)
            with self.assertRaises(type(exc)):
                envolver(abrir, Reloj())(POST)                 # el POST pudo ejecutarse: no se repite
            self.assertEqual(e["llamadas"], 1)

    def test_http_error_nunca(self):
        abrir, e = falla_n(1, urllib.error.HTTPError("http://x", 500, "error", {}, None))
        with self.assertRaises(urllib.error.HTTPError):
            envolver(abrir, Reloj())(GET)
        self.assertEqual(e["llamadas"], 1)

    def test_otros_errores_no(self):
        abrir, e = falla_n(1, urllib.error.URLError(TimeoutError("timed out")))
        with self.assertRaises(urllib.error.URLError):
            envolver(abrir, Reloj())(GET)
        self.assertEqual(e["llamadas"], 1)

    def test_instalar_solo_toca_el_modulo_del_driver(self):
        mod = types.ModuleType("testbench_driver")
        import urllib as u
        mod.urllib = u
        original = urllib.request.urlopen
        reintento.instalar(mod)
        self.assertIsNot(mod.urllib.request.urlopen, original)
        self.assertIs(urllib.request.urlopen, original)         # nadie más ve el cambio
        self.assertIs(mod.urllib.request.Request, urllib.request.Request)
        self.assertIs(mod.urllib.error, urllib.error)


if __name__ == "__main__":
    unittest.main(verbosity=1)
