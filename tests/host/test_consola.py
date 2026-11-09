"""Nivel host de tests/bench/consola.py (H-78): una relectura del banco no cuenta como
reinicio y un reinicio real sí se detecta, aunque sus líneas de arranque sean idénticas
a las del primero. Corre con `python3 tests/host/test_consola.py` (sin dependencias)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "bench"))
import consola  # noqa: E402

ARRANQUE = [
    "ESP-ROM:esp32s3-20210327",
    "rst:0x15 (USB_UART_CHIP_RESET),boot:0x8 (SPI_FAST_FLASH_BOOT)",
    "I (27) boot: ESP-IDF v6.0.2 2nd stage bootloader",
    "I (368) boot: Loaded app from partition at offset 0x20000",
    "I (369) boot: Disabling RNG early entropy source...",
    "I (475) main_task: Calling app_main()",
    "I (485) nodo: boot: clima-f3c6d4 fw=0.0.0-x-bench reset=usb part=ota_0 img=valida",
    "I (545) nodo: med: T=30.8 HR=71.1 Td=24.9",
    "I (695) nodo: wifi: intento 1",
    "I (4115) nodo: wifi: intento 2",
]


def ciclos(desde_ms, n):
    return [f"I ({desde_ms + 60000 * k}) nodo: med: T=30.8 HR=71.1 Td=25.0" for k in range(1, n + 1)]


def entradas(lineas):
    return [{"text": t, "ts": 1000.0 + k} for k, t in enumerate(lineas)]


class Consola(unittest.TestCase):
    def test_relectura_del_arranque_no_es_reinicio(self):
        # Caso de 050dd09: el bloque desde «Loaded app» se entrega dos veces y luego sigue.
        log = ARRANQUE + ARRANQUE[3:] + ["I (4125) wifi:state: init -> auth (0xb0)"] + ciclos(4125, 5)
        limpias, rel = consola.quitar_relecturas(entradas(log))
        self.assertEqual(rel, [(len(ARRANQUE), len(ARRANQUE) - 3, 3)])
        self.assertEqual([e["text"] for e in limpias], ARRANQUE + log[len(ARRANQUE) * 2 - 3:])
        self.assertEqual(consola.reinicios(limpias), [])

    def test_relectura_en_mitad_de_la_ventana(self):
        log = ARRANQUE + ciclos(4115, 10)
        log = log[:12] + log[8:12] + log[12:]
        limpias, rel = consola.quitar_relecturas(entradas(log))
        self.assertEqual(len(rel), 1)
        self.assertEqual(consola.reinicios(limpias), [])

    def test_reinicio_real_con_lineas_identicas_se_detecta(self):
        # Tras 10 ciclos el DUT reinicia y repite su arranque letra por letra.
        log = ARRANQUE + ciclos(4115, 10) + ARRANQUE + ciclos(4115, 3)
        limpias, rel = consola.quitar_relecturas(entradas(log))
        self.assertEqual(rel, [])
        self.assertEqual(len(limpias), len(log))
        r = consola.reinicios(limpias)
        self.assertEqual(len(r), 1)
        self.assertEqual(limpias[r[0]]["text"], "I (27) boot: ESP-IDF v6.0.2 2nd stage bootloader")

    def test_reinicio_real_sin_rst_ni_primeras_lineas_se_detecta(self):
        # Como el segundo arranque de CR-TB-12, pero tarde: sin ROM ni bootloader.
        log = ARRANQUE + ciclos(4115, 10) + ARRANQUE[3:] + ciclos(4115, 3)
        limpias, rel = consola.quitar_relecturas(entradas(log))
        self.assertEqual(rel, [])
        self.assertEqual(len(consola.reinicios(limpias)), 1)

    def test_reinicio_real_al_final_del_log_se_detecta(self):
        # Sin ninguna línea con reloj después de la copia: no se puede llamar relectura.
        log = ARRANQUE + ciclos(4115, 10) + ARRANQUE[3:]
        limpias, rel = consola.quitar_relecturas(entradas(log))
        self.assertEqual(rel, [])
        self.assertEqual(len(consola.reinicios(limpias)), 1)

    def test_desorden_de_decenas_de_ms_no_es_reinicio(self):
        log = ["I (595) wifi:Init dynamic rx buffer num: 32", "I (545) nodo: med: T=30.8 HR=71.1 Td=24.9",
               "I (605) wifi_init: rx ba win: 6"]
        self.assertEqual(consola.reinicios(entradas(log)), [])

    def test_copia_de_menos_de_tres_lineas_cuenta_como_reinicio(self):
        # Demasiado corta para afirmar relectura: se cuenta (lado seguro).
        log = ["I (100000) nodo: a", "I (160000) nodo: b", "I (100000) nodo: a", "I (160000) nodo: b",
               "I (220000) nodo: c"]
        limpias, rel = consola.quitar_relecturas(entradas(log))
        self.assertEqual(rel, [])
        self.assertEqual(len(consola.reinicios(limpias)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
