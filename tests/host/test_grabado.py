"""Nivel host de tests/bench/grabado.py (release v0.0.1, 2026-11-15): con un banco que
recorta los blancos finales del multipart (el defecto del fork hasta b5623c4), la
protección B hace que la imagen llegue entera, y la comprobación de «Wrote N bytes»
detecta cualquier recorte que quede. Corre con `python3 tests/host/test_grabado.py`."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))
import grabado  # noqa: E402

# Cola real de la imagen de v0.0.1 que falló: el SHA-256 añadido termina en 0x0a
COLA_V001 = bytes.fromhex("60b6a606d5e7a0699076466c7095680a")


class BancoSimulado:
    """Imita POST /api/flash: lo que recibe pasa (o no) por bytes.strip() y esptool
    rellena a 4 con 0xFF; guarda lo que quedaría en la flash por offset."""

    def __init__(self, recorta):
        self.recorta, self.flash_mem = recorta, {}

    def flash(self, slot, images, chip="auto", erase=False, timeout=300):
        lineas = []
        for off, ruta in images.items():
            datos = pathlib.Path(ruta).read_bytes()
            if self.recorta:
                datos = datos.strip()          # el defecto: también quita blancos del final
            datos += b"\xff" * (-len(datos) % 4)
            self.flash_mem[off] = datos
            lineas.append(f"Wrote {len(datos)} bytes ({len(datos) // 2} compressed) at 0x{int(off, 16):08x} in 0.1 seconds")
        return {"ok": True, "returncode": 0, "output": "\n".join(lineas) + "\nHash of data verified.\n"}


class TestGrabado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def imagen(self, nombre, datos):
        p = self.dir / nombre
        p.write_bytes(datos)
        return str(p)

    def test_v001_llega_entera_con_la_proteccion(self):
        app = b"\xe9" + bytes(1000) + COLA_V001                   # 1017 bytes, termina en 0x0a
        banco = grabado.envolver(BancoSimulado(recorta=True))
        res = banco.flash("SLOT1", {"0x20000": self.imagen("app.bin", app)})
        self.assertTrue(res["ok"], res.get("error"))
        escrito = banco.flash_mem["0x20000"]
        self.assertEqual(escrito[:len(app)], app)                 # la imagen, byte a byte
        self.assertEqual(set(escrito[len(app):]), {0xFF})         # detrás, solo relleno borrado

    def test_todos_los_blancos_finales(self):
        for b in grabado.BLANCOS:
            app = b"\xe9cuerpo" + bytes([b])
            banco = grabado.envolver(BancoSimulado(recorta=True))
            res = banco.flash("SLOT1", {"0x0": self.imagen(f"a{b}.bin", app)})
            self.assertTrue(res["ok"], f"{b:#04x}: {res.get('error')}")
            self.assertEqual(banco.flash_mem["0x0"][:len(app)], app, f"{b:#04x}")

    def test_sin_blanco_final_no_se_toca(self):
        app = b"\xe9cuerpo\x25"
        rutas, tamanos = grabado.proteger({"0x0": self.imagen("b.bin", app)}, self.dir)
        self.assertEqual(pathlib.Path(rutas["0x0"]).read_bytes(), app)
        self.assertEqual(tamanos, {"0x0": len(app)})

    def test_la_comprobacion_detecta_un_recorte(self):
        # Sin la protección (proteger desactivada), el recorte se ve en «Wrote N bytes»
        app = b"\xe9" + bytes(11) + b"\n\n\n\n"                     # 16 bytes → recortado a 12
        res = BancoSimulado(recorta=True).flash("SLOT1", {"0x20000": self.imagen("c.bin", app)})
        errores = grabado.revisar(res["output"], {"0x20000": len(app)})
        self.assertEqual(len(errores), 1)
        self.assertIn("escribió 12 bytes y se enviaron 16", errores[0])

    def test_la_comprobacion_acepta_el_relleno_de_esptool_y_falla_sin_linea(self):
        self.assertEqual(grabado.revisar("Wrote 8 bytes at 0x00320000 in 0.1 seconds", {"0x320000": 5}), [])
        self.assertEqual(grabado.revisar("Wrote 1079632 bytes (702789 compressed) at 0x00020000 in 5.3 seconds",
                                         {"0x20000": 1079632}), [])
        self.assertTrue(grabado.revisar("", {"0x0": 4}))

    def test_limite_de_wrote_y_por_que_hace_falta_b(self):
        # Un recorte de 1 a 3 bytes queda oculto: esptool rellena al mismo múltiplo de 4.
        # Es el caso de v0.0.1 (1079632 → 1079631 → «Wrote 1079632»). Por eso B (proteger)
        # es la defensa, y JRN-01.0 además falla si el arranque dice «Image hash failed».
        app = b"\xe9" + bytes(14) + b"\n"                              # 16 bytes
        res = BancoSimulado(recorta=True).flash("SLOT1", {"0x20000": self.imagen("d.bin", app)})
        self.assertEqual(grabado.revisar(res["output"], {"0x20000": len(app)}), [])   # no se ve
        banco = grabado.envolver(BancoSimulado(recorta=True))
        self.assertTrue(banco.flash("SLOT1", {"0x20000": self.imagen("e.bin", app)})["ok"])
        self.assertEqual(banco.flash_mem["0x20000"][:len(app)], app)                  # con B llega entera

if __name__ == "__main__":
    unittest.main(verbosity=1)
