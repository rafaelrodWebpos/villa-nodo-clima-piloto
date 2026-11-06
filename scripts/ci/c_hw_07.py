"""TC-HW-07 · C-HW-07 (other, revisión + CI): el firmware (main/, components/) no usa
GPIO0, 3, 19, 20, 38, 43, 44, 45, 46 ni 48. Lista los pines que usa y falla si alguno
está prohibido. Uso: python3 c_hw_07.py [raíz]"""
import pathlib, re, sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
PROHIBIDOS = {0, 3, 19, 20, 38, 43, 44, 45, 46, 48}
PATRONES = [r"GPIO_NUM_(\d+)", r"#define\s+PIN_\w+\s+(\d+)", r"\.\w*_io_num\s*=\s*(\d+)",
            r"gpio_\w+\(\s*(?:\(gpio_num_t\)\s*)?(\d+)\s*[,)]"]
usados, mal = {}, []
for f in list(root.glob("main/**/*.[ch]")) + list(root.glob("components/**/*.[ch]")):
    for n, ln in enumerate(f.read_text(errors="ignore").splitlines(), 1):
        for p in PATRONES:
            for g in re.findall(p, ln):
                pin = int(g); usados.setdefault(pin, []).append(f"{f}:{n}")
                if pin in PROHIBIDOS:
                    mal.append(f"{f}:{n}: GPIO{pin} prohibido por C-HW-07")
print("C-HW-07: pines usados", {k: len(v) for k, v in sorted(usados.items())}, "—", "sin hallazgos" if not mal else f"{len(mal)} hallazgo(s)")
for m in mal: print("  ", m)
sys.exit(1 if mal else 0)
