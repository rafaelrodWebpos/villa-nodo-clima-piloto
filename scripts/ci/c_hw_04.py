"""TC-HW-04 · C-HW-04, C-HW-05 (other, CI): SDA = GPIO8, SCL = GPIO9 y 100 kHz en
la única configuración del bus I²C del firmware (main/, components/; las sondas
de tests/target no son el firmware). Uso: python3 c_hw_04.py [raíz]"""
import pathlib, re, sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
fuentes = list(root.glob("main/**/*.c")) + list(root.glob("components/**/*.c"))
con_bus = [f for f in fuentes if "i2c_new_master_bus(" in f.read_text(errors="ignore")]
mal = []
if len(con_bus) != 1:
    mal.append(f"configuraciones del bus I²C: {len(con_bus)} ({[str(f) for f in con_bus]}); se espera una")
else:
    src = con_bus[0].read_text()
    defs = dict(re.findall(r"#define\s+(\w+)\s+(\d+)", src))
    def valor(campo):
        m = re.search(rf"\.{campo}\s*=\s*(\w+)", src)
        return None if not m else int(defs.get(m.group(1), m.group(1))) if (m.group(1) in defs or m.group(1).isdigit()) else None
    for campo, esperado in (("sda_io_num", 8), ("scl_io_num", 9), ("scl_speed_hz", 100000)):
        v = valor(campo)
        if v != esperado:
            mal.append(f"{con_bus[0]}: .{campo} = {v}, se espera {esperado}")
print("C-HW-04/05:", "sin hallazgos" if not mal else f"{len(mal)} hallazgo(s)")
for m in mal: print("  ", m)
sys.exit(1 if mal else 0)
