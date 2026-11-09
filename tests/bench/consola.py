"""Reinicios en la consola serie del DUT (H-78): funciones puras, sin banco, para que el
nivel host las pruebe (tests/host/test_consola.py).

Un reinicio es un retroceso del reloj de esp_log («I (12345) …», ms desde el arranque):
la aplicación vuelve a contar desde 0. Un texto «boot:» por sí solo no lo prueba: el banco
puede volver a entregar un bloque ya leído con otra marca de tiempo (observado en TC-WDT-01,
20261108T195622Z-050dd09), y esa relectura repite las líneas de arranque.

Una relectura se reconoce porque es una copia idéntica de un bloque anterior y, al quitarla,
el reloj sigue donde estaba antes de la copia. Tras un reinicio real el reloj sigue bajo,
aunque las líneas del arranque coincidan letra por letra con las del primero; por eso el
bloque no se quita y el retroceso se cuenta."""
import re

_RELOJ = re.compile(r"^[IWEDV] \((\d+)\) ")
TOL_MS = 1000          # tareas distintas escriben fuera de orden unas decenas de ms
MIN_BLOQUE = 3         # una o dos líneas iguales no bastan para hablar de relectura


def texto(e):
    return e.get("text", "") if isinstance(e, dict) else str(e)


def reloj_ms(e):
    """ms de esp_log de una entrada, o None si la línea no lo lleva (ROM, wifi sin marca)."""
    m = _RELOJ.match(texto(e).strip())
    return int(m.group(1)) if m else None


def _siguiente_reloj(txt, i):
    for t in txt[i:]:
        r = reloj_ms(t)
        if r is not None:
            return r
    return None


def quitar_relecturas(entradas):
    """(limpias, relecturas): sin los bloques que son relectura del banco.
    relecturas = [(índice en entradas, nº de líneas, índice del original)]."""
    txt = [texto(e).rstrip() for e in entradas]
    primera = {}
    for i, t in enumerate(txt):
        primera.setdefault(t, []).append(i)
    fuera, relecturas = set(), []
    maximo, i = None, 0
    while i < len(txt):
        r = reloj_ms(txt[i])
        if r is not None and maximo is not None and r < maximo - TOL_MS:
            # Retroceso: ¿empieza aquí (o en las líneas sin reloj justo antes) una copia?
            s = i
            while s > 0 and s - 1 not in fuera and reloj_ms(txt[s - 1]) is None:
                s -= 1
            mejor = (0, None)
            for j in primera.get(txt[s], []):
                if j >= s:
                    break
                n = 0
                while s + n < len(txt) and j + n < s and txt[j + n] == txt[s + n]:
                    n += 1
                if n > mejor[0]:
                    mejor = (n, j)
            n, j = mejor
            despues = _siguiente_reloj(txt, s + n)
            if n >= MIN_BLOQUE and despues is not None and despues >= maximo - TOL_MS:
                fuera.update(range(s, s + n))
                relecturas.append((s, n, j))
                i = s + n
                continue
            maximo = r                      # retroceso real: el reloj vuelve a empezar
        elif r is not None:
            maximo = r if maximo is None else max(maximo, r)
        i += 1
    return [e for k, e in enumerate(entradas) if k not in fuera], relecturas


def reinicios(entradas):
    """Índices (en entradas) de las líneas donde el reloj de esp_log retrocede."""
    out, maximo = [], None
    for k, e in enumerate(entradas):
        r = reloj_ms(e)
        if r is None:
            continue
        if maximo is not None and r < maximo - TOL_MS:
            out.append(k)
            maximo = r
        else:
            maximo = r if maximo is None else max(maximo, r)
    return out
