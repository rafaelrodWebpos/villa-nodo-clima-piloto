"""TC-CFG-01 · C-CFG-01 (other, CI): ningún campo de configuración de §17 tiene un
valor inicial no vacío en Kconfig, sdkconfig*.defaults ni el código, y ningún
tópico tiene un prefijo literal. Uso: python3 c_cfg_01.py [raíz]"""
import pathlib, re, sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
CAMPOS = re.compile(r"WIFI|SSID|PASS|MQTT|BROKER|USER|ZONA|SITIO", re.I)   # los 7 campos de cadena de §17
MIME = ("text/", "application/", "image/", "multipart/")                   # literales con «/» que no son tópicos
mal = []

# 1. Kconfig: opciones de §17 con un default de cadena no vacío
for k in list(root.glob("main/Kconfig*")) + list(root.glob("components/*/Kconfig*")):
    sim = None
    for n, ln in enumerate(k.read_text().splitlines(), 1):
        m = re.match(r"\s*(?:menu)?config\s+(\w+)", ln)
        if m: sim = m.group(1)
        m = re.match(r'\s*default\s+"([^"]*)"', ln)
        if m and sim and CAMPOS.search(sim) and m.group(1):
            mal.append(f"{k}:{n}: {sim} con valor inicial no vacío")
# 2. sdkconfig*.defaults
for d in root.glob("sdkconfig*.defaults"):
    for n, ln in enumerate(d.read_text().splitlines(), 1):
        m = re.match(r'(CONFIG_\w+)="([^"]*)"', ln)
        if m and CAMPOS.search(m.group(1)) and m.group(2):
            mal.append(f"{d}:{n}: {m.group(1)} con valor inicial no vacío")
# 3. Código: literales con «/» que parecen un prefijo de tópico
for f in list(root.glob("main/**/*.[ch]")) + list(root.glob("components/**/*.[ch]")):
    for n, ln in enumerate(f.read_text(errors="ignore").splitlines(), 1):
        if ln.lstrip().startswith("#include"):
            continue
        for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', ln):
            if re.match(r"[A-Za-z0-9_-]+/", lit) and not lit.startswith(MIME):
                mal.append(f"{f}:{n}: literal con prefijo de tópico «{lit}»")
print("C-CFG-01:", "sin hallazgos" if not mal else f"{len(mal)} hallazgo(s)")
for m in mal: print("  ", m)
sys.exit(1 if mal else 0)
