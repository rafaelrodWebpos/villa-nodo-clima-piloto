# TC-POR-12 — Portal cerrado a los 10 min (ESPERA)

- imagen: `0.0.0-758ccbc-bench` (variante bench, run CI None)

- Precondiciones: grabar la imagen de la CI en SLOT1 y P-NVS-ERASE
- Reset; el DUT abre el portal (T02)
- a ~30 s de T02, `clima-f3c6d4` visible en el escaneo: sí
- Esperar el cierre del portal (T24, ≈ 10 min desde T02)
- T02 → T24 en el reloj del DUT: 600000 ms (esperado 600000 ± 5000)
- escaneos tras el cierre: ['no', 'no', 'no']
- líneas med: después del cierre: 1; `nvs: config escrita`: 0; reinicios tras T02: 0
- Otro reset: el portal vuelve a abrirse
- log: `TC-POR-12-serie.log` (348 líneas)
- tras el segundo reset, `clima-f3c6d4` visible: sí

**Resultado: PASS** — T24 a 600.0 s de T02; AP fuera en los 3 escaneos; 1 med: en ESPERA; sin NVS ni reinicio; reabierto tras un reset
