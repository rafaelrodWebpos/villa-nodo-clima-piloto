# Visita física final de la Fase 3 (S-C)

Fecha: domingo 2026-11-15 a las 11:00. El banco queda listo antes; las 6 pruebas se lanzan en el
orden de la tabla. Después vienen la auditoría de seguridad S3 y el tag v0.0.1.

Firmware: la imagen de banco del commit vigente ese día (FSD 0.9.10; el firmware es igual al de `bb814d2`). Antes
de que llegues, yo grabo la imagen y dejo el banco listo. Todo lo demás lo lanzo yo desde el
portátil. Tú solo actúas en los pasos de esta lista o cuando el banco muestre un aviso en su
página web (botón «Hecho»).

Regla de los cables (C-HW-01): se desenchufa solo el lado de la **placa** del USB-C. El lado de la
Raspberry Pi no se toca nunca.

| # | Prueba | Qué haces tú | Avisos | Duración |
|---|---|---|---|---|
| 1 | FR-POR-02 con iPhone (H-83, TC-POR-08 alt. manual) | Pasos 1.1–1.6 | ninguno | ~10 min |
| 2 | JRN-01.7: corte de alimentación | desenchufar y volver a enchufar, 1 vez | 2 | ~10 min |
| 3 | TC-CFG-02: 5 cortes con la config intacta | desenchufar y volver a enchufar, 5 veces | 10 | ~30 min |
| 4 | TC-MQTT-04: Last Will en un corte | desenchufar y volver a enchufar, 1 vez | 2 | ~10 min |
| 5 | TC-SEN-04: SDA suelto 3 ciclos | soltar y volver a poner el Dupont de SDA del SHT41 | 2 | ~10 min |
| 6 | TC-OTA-15: corte del USB-C durante la descarga OTA (H-89) | pulsar «Hecho» en el aviso previo y desenchufar en cuanto salga el aviso | 3 | ~15 min |

Total: ~1 h 25 min. Yo lanzo cada prueba en cuanto termina la anterior.

## 1. iPhone (FR-POR-02, H-83)

El DUT queda en PORTAL con la NVS borrada y la red abierta `clima-f3c6d4`.

1.1. En el iPhone, apaga los datos móviles y olvida la red `clima-f3c6d4` si la tiene guardada.
1.2. Únete a `clima-f3c6d4`. Debe abrirse sola la ventana del portal con el formulario «Nodo clima».
1.3. Cierra esa ventana **sin enviar nada**.
1.4. En Safari, abre `http://example.com`. Debe salir el formulario del nodo, no la página real.
1.5. Olvida la red.
1.6. Dime la hora aproximada, el modelo del iPhone, la versión de iOS y lo que viste en 1.2 y 1.4.
     Yo lo contrasto con el log del portal: GET `/hotspot-detect.html` → 302, GET / → formulario,
     ningún POST y el nodo sigue en PORTAL. Se registra como H-83.

## 2 a 4. Cortes del USB-C

Cada corte son dos avisos:
- «desenchufa el cable USB-C del lado de la PLACA… y pulsa Hecho»;
- unos 2 minutos después, «vuelve a enchufar… y pulsa Hecho».

No vuelvas a enchufar antes del segundo aviso. Si un aviso no aparece (CR-TB-11), recarga la página
del banco.

## 5. SDA (TC-SEN-04)

- Primer aviso: suelta el Dupont de SDA del SHT41 en la protoboard.
- Unos 3 minutos después: vuelve a ponerlo.

## 6. Corte del USB-C durante la OTA (TC-OTA-15, H-89)

- **Aviso previo:** ponte junto a la placa y pulsa «Hecho». Con eso sale la OTA (dura unos 30 s).
- **Enseguida:** «desenchufa el USB-C de la PLACA». Hazlo en cuanto salga.
- **Unos 2 minutos después:** «vuelve a enchufar».

Esperado: arranca la imagen anterior con `reset=poweron`, el primer status lleva `fw` = esa imagen
y no hay rollback en 330 s. Si el corte cae cuando la descarga ya terminó, el resultado es not
done: yo vuelvo a grabar la imagen y se repite.

## Resultado (2026-11-15)

| # | Prueba | Resultado | Evidencia |
|---|---|---|---|
| 1 | iPhone, FR-POR-02 (H-83) | En rojo con `fad73ef` (11:01 y 11:08): el DNS del portal no contestaba desde S1. Arreglo `b2fffa7` (IP_PKTINFO, misma protección SEC-06). En verde con `b2fffa7` a las 11:51 | `testing/test-plan.yaml`, TC-POR-08 (manual_evidence); regresión del portal en `test-results/20261115T154209Z-2b618eb/` y TC-POR-12 en `test-results/20261115T160658Z-2b618eb/` |
| 2 | JRN-01.7 | PASS | `test-results/20261115T151120Z-fad73ef/` |
| 3 | TC-CFG-02 | PASS (5 encendidos, ningún portal) | ídem |
| 4 | TC-MQTT-04 | PASS (Last Will retenido en ≤ 83 s) | ídem |
| 5 | TC-SEN-04 | PASS | ídem |
| 6 | TC-OTA-15 | PASS con `b2fffa7`: corte al 50 %, arranca A con reset=poweron, 330 s sin rollback (antes: un FAIL por defecto de la prueba y un not done) | `test-results/20261115T155746Z-2b618eb/` |

Las pruebas 2 a 5 corrieron sobre `fad73ef`; `b2fffa7` solo cambia el DNS del portal
(`components/portal/portal_dns.c`, `portal_origen.c`, `main.c` y `CONFIG_LWIP_NETBUF_RECVINFO`).
