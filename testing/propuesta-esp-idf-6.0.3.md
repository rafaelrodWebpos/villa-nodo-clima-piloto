# Propuesta: subir ESP-IDF de v6.0.2 a v6.0.3 (sin aplicar)

- **Motivo:** el aviso GHSA-ch63-jxm5-vmvf de Espressif (severidad alta, publicado el 2026-10-30): «Stack-Based Buffer
  Overflow in lwIP DNS Cache Lookup with Multiple IP Addresses». Afecta a v6.0.2 y está corregido en v6.0.3, que se
  publicó el 2026-09-02.
- **Hoy no es explotable en el nodo.** El fallo necesita varias IP por nombre en la caché DNS, y la imagen del tag
  v0.0.1 tiene `CONFIG_LWIP_DNS_MAX_HOST_IP=1` (`sdkconfig.generated` del artefacto; es el valor por defecto de
  ESP-IDF). El nodo resuelve `pool.ntp.org` (SNTP), el broker si se configura por nombre y `github.com` /
  `release-assets.githubusercontent.com` (OTA).
- **Por qué subir de todos modos:** el riesgo depende de un valor por defecto que un cambio futuro de
  configuración podría cambiar sin que nadie lo note. Además, SEC-15 (§19.3) pide revisar los avisos de ESP-IDF
  antes de cada release.
- **Urgencia:** una precaución, no algo obligatorio. Propongo hacerlo antes de la instalación en la villa (S2),
  junto con A3-02 y A3-03, para pagar una sola regresión y una sola visita.

## Cambios (todos en el repositorio, ninguno en el banco)

| Archivo | Cambio |
|---|---|
| `.github/workflows/build.yml` | `IDF_TAG: v6.0.3`; contenedor `espressif/idf:v6.0.3@sha256:54278f2c01e6e759502e2f04c9103589c17528923426f4d63193490c7a08f555` (digest leído hoy con `docker buildx imagetools inspect`; se vuelve a comprobar al aplicar) |
| `.github/workflows/ota-test.yml` | La misma imagen fijada por digest |
| `.devcontainer/Dockerfile` | `FROM espressif/idf:v6.0.3@sha256:…` y reconstruir `nodo-clima-piloto-dev:latest`. El workflow `devcontainer image builds` lo comprueba |
| `dependencies.lock` | `idf: 6.0.3`, regenerado por el build y no a mano. Se revisa que `espressif/mqtt` no cambie |
| `docs/Functionality/FSD-nodo-clima.md` | La versión exacta de ESP-IDF es HOW. La única mención está en el historial 0.9.9 y es histórica, así que no cambia. No hace falta una versión nueva del FSD |
| `docs/Method/standards/testing.md`, `docs/Method/project/arquitectura.md` | Donde citen v6.0.2, cambiar a v6.0.3 |
| Nueva comprobación en la CI | Que `CONFIG_LWIP_DNS_MAX_HOST_IP=1` siga en el `sdkconfig` de toda imagen, mientras se use un ESP-IDF afectado (defensa mientras tanto; se puede dejar después) |

C-BLD-03 (TC-BLD-03) pide «ESP-IDF v6.x», así que sigue pasando.

## Verificación

1. CI: host, build de producción y de banco, imagen del devcontainer y `ota-test.yml` en seco (sin publicar).
2. Banco, sin acción física:
   - La regresión completa: JRN-01.0 a 01.4, las del portal, MQTT, OTA (TC-OTA-06 a 14, JRN-02.1 y 02.2) y TC-POR-12.
   - El ensayo de `verify` con la imagen de producción.
   - Unos 90 min de banco, en contenedores desacoplados.
3. **Física, obligatoria:** el cambio toca lwIP y el DNS, que sirven a FR-POR-02, así que la evidencia manual H-83
   vence. Hay que repetir la prueba del iPhone (unos 10 min) y conviene juntarla con la visita de S2.
4. Para publicar: un tag nuevo (por ejemplo v0.0.2), que lo crea el propietario. v0.0.1 no se toca.
   - La OTA de v0.0.1 a v0.0.2 queda cubierta por el anti-downgrade (FR-OTA-05).
   - Antes de la instalación se puede probar en el banco con JRN-02.1 adaptada a releases `v*`.

## Riesgos

- ESP-IDF v6.0.3 puede cambiar el tamaño de la app (hoy le sobran 2 MB en `ota_0`), los mensajes del log que
  esperan las pruebas o el comportamiento de lwIP. La regresión completa los cubre.
- El digest de la imagen tiene que tener al menos dos semanas, como pide la norma de dependencias del repo. La imagen v6.0.3 es
  del 2026-09-02, así que la cumple.
