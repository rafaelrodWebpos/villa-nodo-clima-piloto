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



def vivo(t_arranque, ms_lista, texto="nodo: alive {n}", desfase=0.0):
    """Líneas de un arranque en t_arranque, con su llegada al banco = arranque + ms + desfase."""
    return [{"text": f"I ({ms}) " + texto.format(n=i + 1), "ts": t_arranque + ms / 1000 + desfase}
            for i, ms in enumerate(ms_lista)]


class LineasViejas(unittest.TestCase):
    """quitar_viejas (upstream #89, punto 3; 2026-11-22)."""

    def test_reenvio_de_lineas_viejas_se_quita_y_no_es_reinicio(self):
        # arranque a t=1000; ventana de 60 s a partir de ~180 s; el banco reenvía alive 1–3 con hora nueva
        antes = vivo(1000, [181000, 183000, 185000])
        viejas = [{"text": f"I ({ms}) nodo: alive {n}", "ts": 1186.0} for n, ms in ((1, 1000), (2, 2000), (3, 3000))]
        despues = vivo(1000, [187000, 189000])
        entradas = antes + viejas + despues
        limpias, quitadas = consola.quitar_viejas(entradas)
        self.assertEqual(quitadas, [3, 4, 5])
        self.assertEqual(limpias, antes + despues)
        self.assertEqual(consola.reinicios(limpias), [])           # sin el filtro, contaría un reinicio
        self.assertEqual(len(consola.reinicios(entradas)), 1)

    def test_reinicio_real_se_conserva(self):
        a = vivo(1000, [100000, 102000, 104000])
        b = vivo(1110, [300, 500, 2000, 4000])                      # el DUT se reinició a t≈1110
        limpias, quitadas = consola.quitar_viejas(a + b)
        self.assertEqual(quitadas, [])
        self.assertEqual(len(consola.reinicios(limpias)), 1)

    def test_reinicio_real_al_final_con_una_sola_linea(self):
        a = vivo(1000, [100000, 102000])
        b = vivo(1110, [300])
        self.assertEqual(consola.quitar_viejas(a + b)[1], [])

    def test_sellado_unico_de_serial_reset_no_se_quita(self):
        # serial/reset devuelve el arranque con la hora del final de su lectura de 5 s
        a = vivo(1000, [100000, 102000])
        reset = [{"text": f"I ({ms}) boot: x", "ts": 1115.0} for ms in (27, 433, 513, 2000)]
        siguiente = vivo(1110, [6000, 8000, 10000])                 # luego llegan a su hora real
        limpias, quitadas = consola.quitar_viejas(a + reset + siguiente)
        self.assertEqual(quitadas, [])
        self.assertEqual(len(consola.reinicios(limpias)), 1)

    def test_latencia_a_rafagas_no_se_quita(self):
        a = vivo(1000, [100000, 102000, 104000], desfase=0.0) + vivo(1000, [106000], desfase=7.0) + vivo(1000, [108000])
        self.assertEqual(consola.quitar_viejas(a)[1], [])

    def test_lineas_sin_reloj_o_sin_hora_se_conservan(self):
        a = vivo(1000, [100000, 102000])
        sin = [{"text": "ESP-ROM:esp32s3-20210327", "ts": 1186.0}, {"text": "I (1000) nodo: alive 1", "ts": 0},
               "texto suelto"]
        limpias, quitadas = consola.quitar_viejas(a + sin + vivo(1000, [104000]))
        self.assertEqual(quitadas, [])
        self.assertEqual(len(limpias), 6)

    def test_tramo_largo_seguido_del_viejo_cuenta_como_arranque(self):
        a = vivo(1000, [100000, 102000])
        b = vivo(1110, list(range(300, 300 + 25 * 1000, 1000)))     # 25 líneas de un arranque nuevo
        viejo = vivo(1000, [104000])                                 # una línea vieja reaparece
        limpias, quitadas = consola.quitar_viejas(a + b + viejo)
        self.assertNotIn(2, quitadas)                               # el arranque nuevo se conserva
        self.assertEqual(quitadas, [len(a + b)])                   # y la línea vieja se quita


if __name__ == "__main__":
    unittest.main(verbosity=2)
