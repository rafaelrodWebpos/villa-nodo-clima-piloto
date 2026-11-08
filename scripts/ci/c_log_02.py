"""TC-LOG-07 · C-LOG-02 (other, CI + revisión).

Dos usos:
  python3 c_log_02.py fuente             el lector de comandos de la consola (E13) solo se
                                         compila con CONFIG_NODO_BENCH_BUILD: ninguna lectura
                                         de la consola ni cadena de E13 fuera de #if de ese símbolo
  python3 c_log_02.py imagen <bin> <variante>
                                         «wdt-test» y «wdt: bloqueando medicion» ausentes en
                                         la imagen de producción y presentes en la de banco
"""
import pathlib, re, sys

CADENAS = [b"wdt-test", b"wdt: bloqueando medicion"]
# Lecturas de la consola o comandos de E13 que no pueden quedar fuera del símbolo
VIGILADOS = re.compile(r'uart_read_bytes|uart_driver_install|\bfgets\s*\(|\bgetchar\s*\(|\bgetc\s*\(|\bstdin\b|'
                       r'\bscanf\s*\(|usb_serial_jtag_read_bytes|"wdt-test"|"reiniciar"|wdt: bloqueando')


def fuente():
    mal = []
    for f in sorted(pathlib.Path("main").rglob("*.c")) + sorted(pathlib.Path("components").rglob("*.c")):
        pila = []        # por cada #if abierto: ¿es de CONFIG_NODO_BENCH_BUILD (y no estamos en su #else)?
        for n, ln in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            s = ln.strip()
            if re.match(r"#\s*if", s):
                pila.append(bool(re.match(r"#\s*if\s+(defined\s*\(?\s*)?CONFIG_NODO_BENCH_BUILD\b", s)))
            elif re.match(r"#\s*(else|elif)", s) and pila:
                pila[-1] = False
            elif re.match(r"#\s*endif", s) and pila:
                pila.pop()
            elif VIGILADOS.search(ln) and not any(pila) and not s.startswith(("/*", "*", "//")):
                mal.append(f"{f}:{n}: fuera de CONFIG_NODO_BENCH_BUILD: {s[:90]}")
    print("C-LOG-02 (fuente):", "sin hallazgos" if not mal else f"{len(mal)} hallazgo(s)")
    for m in mal:
        print("  ", m)
    return 1 if mal else 0


def imagen(binario, variante):
    datos = pathlib.Path(binario).read_bytes()
    vistas = {c.decode(): c in datos for c in CADENAS}
    quiero = variante != "production"
    mal = [f"«{c}» {'ausente' if quiero else 'presente'}" for c, v in vistas.items() if v != quiero]
    print(f"C-LOG-02 (imagen {variante}):", "sin hallazgos" if not mal else "; ".join(mal), vistas)
    return 1 if mal else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["fuente"]:
        sys.exit(fuente())
    if a[:1] == ["imagen"] and len(a) == 3:
        sys.exit(imagen(a[1], a[2]))
    sys.exit(__doc__)
