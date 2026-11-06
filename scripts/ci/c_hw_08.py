"""TC-HW-08 · C-HW-08 (other, revisión): consola primaria UART0 y secundaria
USB-Serial/JTAG en la configuración. Uso: python3 c_hw_08.py <sdkconfig o sdkconfig.defaults>…"""
import re, sys

mal = []
for f in sys.argv[1:]:
    t = open(f).read()
    si = lambda k: re.search(rf"^{k}=y$", t, re.M) is not None
    if not si("CONFIG_ESP_CONSOLE_UART_DEFAULT") and not re.search(r"^CONFIG_ESP_CONSOLE_UART_NUM=0$", t, re.M):
        mal.append(f"{f}: la consola primaria no es UART0")
    if si("CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG") or si("CONFIG_ESP_CONSOLE_USB_CDC"):
        mal.append(f"{f}: consola primaria en USB")
    if not si("CONFIG_ESP_CONSOLE_SECONDARY_USB_SERIAL_JTAG"):
        mal.append(f"{f}: sin consola secundaria USB-Serial/JTAG")
print("C-HW-08:", "sin hallazgos en " + ", ".join(sys.argv[1:]) if not mal else f"{len(mal)} hallazgo(s)")
for m in mal: print("  ", m)
sys.exit(1 if mal or len(sys.argv) < 2 else 0)
