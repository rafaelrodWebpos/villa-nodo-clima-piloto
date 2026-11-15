"""Grabado por el banco con los bytes exactos (2026-11-15, release v0.0.1).

El POST /api/flash del banco (fork hasta villa-2 b5623c4) pasaba cada parte del
multipart por bytes.strip(): un binario que terminaba en \\n, \\r, espacio, tab,
\\x0b o \\x0c perdía esos bytes, esptool rellenaba con 0xFF y el bootloader
rechazaba la imagen («Image hash failed»). Dos defensas, para cualquier versión:

B. proteger(): si el último byte de una imagen es de esos, se graba una copia con
   4 bytes 0xFF al final. 0xFF es el estado borrado de la flash, así que la
   imagen no cambia; solo deja de terminar en un blanco.
Comprobación. revisar(): la salida de esptool tiene que decir, para cada offset,
   «Wrote N bytes» con N = tamaño enviado redondeado a 4. Si no, la grabación
   falla con un motivo claro aunque esptool haya dicho «Hash of data verified»
   (lo verifica contra lo que recibió, no contra lo que se mandó). Límite: un
   recorte de 1 a 3 bytes no se ve (esptool rellena al mismo múltiplo de 4; fue el
   caso de v0.0.1), así que B es la defensa y JRN-01.0 falla además si el arranque
   dice «Image hash failed».

Solo biblioteca estándar: lo prueba tests/host/test_grabado.py en la CI.
"""
import pathlib
import re
import tempfile

BLANCOS = b" \t\n\r\x0b\x0c"
RELLENO = b"\xff" * 4
WROTE = re.compile(r"Wrote (\d+) bytes(?: \(\d+ compressed\))? at 0x([0-9a-fA-F]+)")


def proteger(images, tmp_dir):
    """{offset: ruta} → ({offset: ruta a grabar}, {offset: bytes enviados})."""
    salida, tamanos = {}, {}
    for off, ruta in images.items():
        datos = pathlib.Path(ruta).read_bytes()
        if datos and datos[-1] in BLANCOS:
            datos += RELLENO
            copia = pathlib.Path(tmp_dir) / f"protegida_{int(off, 16):08x}_{pathlib.Path(ruta).name}"
            copia.write_bytes(datos)
            ruta = str(copia)
        salida[off] = str(ruta)
        tamanos[off] = len(datos)
    return salida, tamanos


def revisar(salida_esptool, tamanos):
    """Lista de discrepancias entre lo enviado y lo que esptool dice que escribió."""
    escritos = {int(o, 16): int(n) for n, o in WROTE.findall(salida_esptool or "")}
    errores = []
    for off, n in tamanos.items():
        esperado = (n + 3) // 4 * 4
        got = escritos.get(int(off, 16))
        if got is None:
            errores.append(f"{off}: esptool no dice «Wrote … bytes» ({n} bytes enviados)")
        elif got != esperado:
            errores.append(f"{off}: esptool escribió {got} bytes y se enviaron {n} (esperado {esperado}): "
                           "el banco alteró la imagen")
    return errores


def envolver(tb):
    """Sustituye tb.flash por una versión que protege las imágenes y revisa la salida."""
    original = tb.flash

    def flash(slot, images, chip="auto", erase=False, timeout=300):
        with tempfile.TemporaryDirectory(prefix="grabado-") as tmp:
            rutas, tamanos = proteger(images, tmp)
            res = original(slot, rutas, chip=chip, erase=erase, timeout=timeout)
        if res.get("ok"):
            errores = revisar(res.get("output") or res.get("log") or "", tamanos)
            if errores:
                res = dict(res, ok=False, error="grabado inexacto: " + "; ".join(errores))
        return res

    tb.flash = flash
    return tb
