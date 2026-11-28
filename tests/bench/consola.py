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


# --------------------------------------------------------------------------
# Líneas viejas reenviadas por el banco con otra hora (upstream #89, punto 3; 2026-11-22)
# --------------------------------------------------------------------------
# El búfer serie del banco a veces devuelve líneas de minutos antes (p. ej. las primeras de
# un arranque) con una hora de llegada nueva, sobre todo tras reenchufar o reabrir el puerto.
# Cada línea con reloj de esp_log da una estimación del instante del arranque:
#     arranque ≈ ts (llegada al banco, s) − ms/1000.
# Las líneas de un mismo arranque coinciden en esa estimación (± la latencia del banco, que va a
# ráfagas, y el sellado único de serial/reset, de hasta ~5 s). Una línea vieja reenviada da una
# estimación que no cuadra y, tras ella, las líneas vuelven a la de antes; un reinicio real da
# una estimación nueva y las líneas siguientes no vuelven a la anterior.
TOL_ARRANQUE_S = 10.0   # más que la latencia del banco y el sellado de serial/reset (5 s)
LARGO = 20              # un tramo así de largo es un arranque real aunque después reaparezca el viejo


def arranque_s(e):
    """Estimación del instante del arranque (s, reloj del banco) o None."""
    r = reloj_ms(e)
    ts = e.get("ts") if isinstance(e, dict) else None
    if r is None or not ts:
        return None
    return float(ts) - r / 1000.0


def quitar_viejas(entradas, tol_s=TOL_ARRANQUE_S, largo=LARGO):
    """(limpias, viejas): sin las líneas que el banco reenvió con otra hora.
    viejas = índices (en entradas) de las líneas quitadas. Las líneas sin reloj o sin ts se
    conservan siempre."""
    est = [arranque_s(e) for e in entradas]
    con = [k for k, a in enumerate(est) if a is not None]
    fuera, actual, p, ultima_ts = set(), None, 0, None
    while p < len(con):
        k = con[p]
        a = est[k]
        if actual is None or abs(a - actual) <= tol_s:
            actual = a if actual is None else actual
            ultima_ts = float(entradas[k]["ts"])
            p += 1
            continue
        # Desacuerdo: tramo de líneas seguidas que tampoco cuadran con el arranque actual
        q = p
        while q < len(con) and abs(est[con[q]] - actual) > tol_s:
            q += 1
        tramo = con[p:q]
        vuelve = q < len(con)                      # tras el tramo, alguna línea vuelve a cuadrar
        coherente = all(abs(est[j] - a) <= tol_s for j in tramo)
        despues = a >= ultima_ts - tol_s           # un reinicio real empieza tras la última línea vista
        if coherente and despues and (not vuelve or len(tramo) >= largo):
            actual = a                             # arranque nuevo confirmado: reinicio real
            ultima_ts = float(entradas[k]["ts"])
            p += 1
            continue
        fuera.update(tramo)                        # reenvío del banco: fuera
        p = q
    return [e for k, e in enumerate(entradas) if k not in fuera], sorted(fuera)
