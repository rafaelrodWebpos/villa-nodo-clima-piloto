"""Comprobaciones sobre la imagen construida (job build de build.yml, con ESP-IDF):
TC-HW-01 · C-HW-01/02: cabeceras del bootloader y de la app declaran 8 MB (nunca «detect»).
TC-HW-03 (parte CI) · C-HW-03: PSRAM deshabilitada en el sdkconfig de la imagen.
TC-HW-08 (parte CI) · C-HW-08: consola de la imagen (c_hw_08.py sobre build/sdkconfig).
TC-BLD-01 · C-BLD-01: gen_esp32part.py sobre la tabla de la imagen = tabla de FSD §2.2.
TC-BLD-02 · C-BLD-02: check_sizes.py rechaza una app de 0x300001 bytes y acepta la real.
TC-BLD-03 · C-BLD-03: ESP-IDF v6.x y target esp32s3.
Uso: python3 build_checks.py <dir de build> <nombre de la app>"""
import os, pathlib, re, subprocess, sys, tempfile

b = pathlib.Path(sys.argv[1]); app = b / f"{sys.argv[2]}.bin"; idf = os.environ["IDF_PATH"]
fsd = pathlib.Path("docs/Functionality/FSD-nodo-clima.md").read_text()
mal, ok = [], []
def chk(cond, bien, malo): (ok if cond else mal).append(bien if cond else malo)

# C-HW-01/02: byte 3 de la cabecera, nibble alto = tamaño de flash (ESP32-S3: 3 = 8 MB)
TAM = {0: "1MB", 1: "2MB", 2: "4MB", 3: "8MB", 4: "16MB", 5: "32MB"}
for img in (b / "bootloader" / "bootloader.bin", app):
    h = img.read_bytes()[:4]
    t = TAM.get(h[3] >> 4, f"código {h[3] >> 4:#x}")
    chk(h[0] == 0xE9 and t == "8MB", f"C-HW-01/02: {img.name} declara 8MB", f"C-HW-01/02: {img.name} declara {t} (magic {h[0]:#x})")
sdk = (b / "sdkconfig").read_text()
# C-HW-03
chk("# CONFIG_SPIRAM is not set" in sdk and "CONFIG_SPIRAM=y" not in sdk, "C-HW-03: PSRAM deshabilitada", "C-HW-03: la imagen activa la PSRAM")
# C-HW-08
r = subprocess.run([sys.executable, "scripts/ci/c_hw_08.py", str(b / "sdkconfig")], capture_output=True, text=True)
chk(r.returncode == 0, "C-HW-08: consola UART0 + USB-Serial/JTAG en la imagen", "C-HW-08: " + r.stdout.strip())
# C-BLD-01: tabla de la imagen frente a la de §2.2
tabla = b / "partition_table" / "partition-table.bin"
csv = subprocess.run([sys.executable, f"{idf}/components/partition_table/gen_esp32part.py", str(tabla)],
                     capture_output=True, text=True, check=True).stdout
img_rows = [tuple(c.strip().lower() for c in l.split(",")[:5]) for l in csv.splitlines() if l and not l.startswith("#")]
sec = fsd[fsd.index("**Tabla de particiones (normativa).**"):fsd.index("- **C-BLD-01**")]
fsd_rows = [tuple(c.strip().split(" ")[0].lower() for c in l.strip("|").split("|"))
            for l in sec.splitlines() if l.startswith("| ") and not l.startswith("| Nombre")]
def num(x):
    x = x.strip().upper()
    if x.endswith("K"): return int(x[:-1], 0) * 1024
    if x.endswith("M"): return int(x[:-1], 0) * 1024 * 1024
    return int(x, 0)
def norm(r):
    n, t, s, o, z = r
    return (n, t, s, num(o), num(z))
chk([norm(r) for r in img_rows] == [norm(r) for r in fsd_rows], f"C-BLD-01: tabla de la imagen = §2.2 ({len(fsd_rows)} filas)",
    f"C-BLD-01: tabla de la imagen {img_rows} ≠ §2.2 {fsd_rows}")
# C-BLD-02: la regla de tamaño (3 MB) la aplica check_sizes.py del build
cs = f"{idf}/components/partition_table/check_sizes.py"
with tempfile.NamedTemporaryFile(suffix=".bin") as big:
    big.write(b"\0" * 0x300001); big.flush()
    r1 = subprocess.run([sys.executable, cs, "--offset", "0x8000", "partition", "--type", "app", str(tabla), big.name], capture_output=True, text=True)
r2 = subprocess.run([sys.executable, cs, "--offset", "0x8000", "partition", "--type", "app", str(tabla), str(app)], capture_output=True, text=True)
chk(r1.returncode != 0 and "small" in (r1.stdout + r1.stderr).lower(), "C-BLD-02: una app de 0x300001 bytes hace fallar el build (too small)",
    f"C-BLD-02: check_sizes no rechaza 0x300001 bytes (rc {r1.returncode}: {(r1.stdout + r1.stderr).strip()[:160]})")
chk(r2.returncode == 0, "C-BLD-02 (control): la app real cabe", f"C-BLD-02 (control): la app real no cabe ({r2.stdout.strip()[:120]})")
# C-BLD-03
v = subprocess.run(["idf.py", "--version"], capture_output=True, text=True).stdout.strip()
chk(re.search(r"\bv6\.\d", v) is not None, f"C-BLD-03: {v}", f"C-BLD-03: versión {v!r}, no 6.x")
chk('CONFIG_IDF_TARGET="esp32s3"' in sdk, "C-BLD-03: target esp32s3", "C-BLD-03: target distinto de esp32s3")
for m in ok: print("ok   ", m)
for m in mal: print("FALLA", m)
sys.exit(1 if mal else 0)
