# Visita física final de la Fase 3 (S-C)

Firmware: la imagen de banco de `32027b0` (FSD 0.9.10; el firmware es igual al de `bb814d2`). Antes
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
| 6 | Corte del USB-C durante una OTA (pendiente de aprobación, ver abajo) | desenchufar justo después del aviso | 2 | ~10 min |

Total: ~1 h 20 min. Yo lanzo cada prueba en cuanto termina la anterior.

## 1. iPhone (FR-POR-02, H-83)

El DUT queda en PORTAL con la NVS borrada y la red abierta `clima-f3c6d4`.

1.1. En el iPhone, apaga los datos móviles y olvida la red `clima-f3c6d4` si la tiene guardada.
1.2. Únete a `clima-f3c6d4`. Debe abrirse sola la ventana del portal con el formulario «Nodo clima».
1.3. Cierra esa ventana **sin enviar nada**.
1.4. En Safari, abre `http://example.com`. Debe salir el formulario del nodo, no la página real.
1.5. Olvida la red.
1.6. Dime la hora aproximada, el modelo del iPhone, la versión de iOS y lo que viste en 1.2 y 1.4.
     Yo lo contrasto con el log del portal: GET `/hotspot-detect.html` → 302, GET / → formulario,
     ningún POST y el nodo sigue en PORTAL. Tú le pones el número H-NN al registro.

## 2 a 4. Cortes del USB-C

Cada corte son dos avisos:
- «desenchufa el cable USB-C del lado de la PLACA… y pulsa Hecho»;
- unos 2 minutos después, «vuelve a enchufar… y pulsa Hecho».

No vuelvas a enchufar antes del segundo aviso. Si un aviso no aparece (CR-TB-11), recarga la página
del banco.

## 5. SDA (TC-SEN-04)

- Primer aviso: suelta el Dupont de SDA del SHT41 en la protoboard.
- Unos 3 minutos después: vuelve a ponerlo.

## 6. Corte del USB-C durante la OTA (falta tu aprobación)

El FSD no tiene un contrato propio para este caso. El más cercano es T17, cuya columna «No debe
ocurrir» dice: marcar arrancable el slot nuevo antes de verificar la imagen completa. Lo esperado es
que, al volver la alimentación, arranque A (`boot: … fw=A part=<slot de A>`), sin rollback, y que
el primer status lleve `fw` = A.

La descarga dura unos 29 s (de «ota: 0 %» a «ota: 100 %»). La prueba manda el comando y avisa
«desenchufa ahora». Solo vale si el último «ota: n %» antes del corte es menor que 100; si no,
se repite.

Hace falta un test nuevo, TC-OTA-15, y su fila en el plan (~20 min de trabajo mío, sin banco).
Lo escribo cuando lo apruebes, antes de la visita.
