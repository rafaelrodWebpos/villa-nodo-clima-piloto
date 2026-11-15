"""Comprobaciones de las imágenes de prueba OTA (auditoría H-91).

A3-04 · FR-OTA-05/13: toda versión de una pre-release ota-test-* queda por debajo de toda
versión v* en la precedencia semver, para que una imagen de prueba nunca pueda bloquear con el
anti-downgrade la vuelta a una release, ni pasar por una release. La base es v0.0.1 (primer tag,
H-37) aunque todavía no exista, y además cada tag v* publicado.

A3-05 · FR-OTA-07: CONFIG_NODO_TEST_SIN_MQTT (imagen que nunca llega a OPERATIVO, solo para
JRN-02.2) está apagado en el sdkconfig de toda imagen que no sea de prueba.

Uso:
  ota_prueba.py versiones <versión de prueba>... [-- <tag v*>...]
  ota_prueba.py sin_mqtt <sdkconfig> <variante>
  ota_prueba.py autoprueba
"""
import re
import sys

SEMVER = re.compile(r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$")
PRIMER_TAG = "v0.0.1"


def clave(v):
    m = SEMVER.match(v)
    if not m:
        raise ValueError(f"no semver: {v}")
    pre = m.group(4)
    ids = [] if pre is None else [(0, int(x), "") if x.isdigit() else (1, 0, x) for x in pre.split(".")]
    # sin prerelease va después de cualquier prerelease de la misma versión
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), pre is None, ids)


def versiones(prueba, tags):
    errores = []
    tags = sorted({t for t in tags + [PRIMER_TAG] if t.startswith("v")}, key=clave)
    for v in prueba:
        m = SEMVER.match(v)
        if not m or not m.group(4) or not m.group(4).startswith("ota-test."):
            errores.append(f"{v}: no es una versión de prueba 0.0.1-ota-test.<serie>.<n>")
            continue
        altas = [t for t in tags if clave(v) >= clave(t)]
        if altas:
            errores.append(f"{v} no queda por debajo de {', '.join(altas)}")
    return errores


def sin_mqtt(sdkconfig_txt, variante):
    activo = re.search(r"^CONFIG_NODO_TEST_SIN_MQTT=y$", sdkconfig_txt, re.M) is not None
    if variante in ("production", "bench", "bench-sin-receptor") and activo:
        return [f"CONFIG_NODO_TEST_SIN_MQTT=y en la imagen {variante}"]
    return []


def autoprueba():
    casos = [
        (versiones(["0.0.1-ota-test.2.1", "0.0.1-ota-test.999.3"], []), True),
        (versiones(["0.0.1-ota-test.2.1"], ["v0.0.1", "v0.1.0"]), True),
        (versiones(["0.0.2-ota-test.1.1"], []), False),            # por encima de v0.0.1
        (versiones(["0.0.1"], []), False),                         # sin prerelease
        (versiones(["1.0.0-ota-test.1.1"], ["v0.0.1"]), False),
        (versiones(["0.0.1-rc.1"], []), False),                    # no es ota-test
        (versiones(["x"], []), False),
        (sin_mqtt("CONFIG_NODO_TEST_SIN_MQTT=y\n", "production"), False),
        (sin_mqtt("CONFIG_NODO_TEST_SIN_MQTT=y\n", "bench"), False),
        (sin_mqtt("# CONFIG_NODO_TEST_SIN_MQTT is not set\n", "production"), True),
        (sin_mqtt("", "production"), True),
    ]
    assert clave("0.0.1-ota-test.2.10") > clave("0.0.1-ota-test.2.9") and clave("0.0.1-ota-test.2.1") < clave("0.0.1")
    malos = [i for i, (err, debe_pasar) in enumerate(casos) if (not err) != debe_pasar]
    return [f"autoprueba: caso {i} no da lo esperado" for i in malos]


def main(a):
    if a[:1] == ["versiones"]:
        resto = a[1:]
        corte = resto.index("--") if "--" in resto else len(resto)
        errores = versiones(resto[:corte], resto[corte + 1:])
    elif a[:1] == ["sin_mqtt"] and len(a) == 3:
        errores = sin_mqtt(open(a[1]).read(), a[2])
    elif a == ["autoprueba"]:
        errores = autoprueba()
    else:
        print(__doc__)
        return 2
    for e in errores:
        print("FALLA", e)
    if not errores:
        print("ok   ", " ".join(a[:1]))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
