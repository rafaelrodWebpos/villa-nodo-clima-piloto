/* Portal cautivo — TODOS los textos visibles, en un solo lugar (diseño H-36,
 * aprobado como provisional por el propietario, con los cambios de H-37; no
 * forma parte del FSD).
 * Cambiar un texto aquí no cambia ningún test: los tests verifican los
 * atributos name de §17, no las etiquetas. Ningún ejemplo es un valor real. */
#pragma once

#define TX_TITULO           "Nodo clima"
#define TX_FIRMWARE         "firmware"

#define TX_BLOQUE_WIFI      "Wi-Fi de la casa"
#define TX_RED              "Red"
#define TX_CLAVE            "Contraseña"

#define TX_BLOQUE_MQTT      "Servidor MQTT"
#define TX_SERVIDOR         "Servidor"
#define TX_PUERTO           "Puerto"
#define TX_USUARIO_OPC      "Usuario (opcional)"
#define TX_CLAVE_OPC        "Contraseña (opcional)"

#define TX_BLOQUE_UBICACION "Ubicación"
#define TX_SITIO            "Sitio"
#define TX_ZONA             "Zona"
#define TX_AYUDA_ID         "minúsculas, números, - y _"   /* bajo Sitio y Zona */

/* Ejemplos genéricos (placeholder); nunca un valor real (C-CFG-01) */
#define TX_EJ_RED           "nombre de tu Wi-Fi"
#define TX_EJ_SERVIDOR      "homeassistant.local"
#define TX_EJ_SITIO         "sitio1"
#define TX_EJ_ZONA          "zona1"

#define TX_GUARDAR          "Guardar y conectar"
#define TX_MOSTRAR_CLAVE    "Mostrar u ocultar la contraseña"

/* Pantallas y avisos de los pasos siguientes (FR-POR-04/05/06) */
#define TX_AVISO_ERRORES    "Revisa los campos marcados. No se guardó nada."
#define TX_PROBANDO         "Probando la conexión…"
#define TX_NO_CONECTA       "No se pudo conectar…"
#define TX_CONECTADO        "Conectado. El nodo se reinicia…"
/* T07: un envío mientras ya se prueba una conexión. BORRADOR del asistente,
 * pendiente de revisión del propietario (H-36 no lo fija). */
#define TX_OCUPADO          "Ya se está probando una conexión. Espera unos segundos."

/* Mensaje bajo cada campo inválido (FR-POR-04). Redactados por el asistente y
 * aprobados tal cual por el propietario el 2026-11-03 (H-36 fija el aviso
 * general; estos completan el diseño). */
#define TX_ERR_WIFI_SSID    "Escribe el nombre de la red (1 a 32 caracteres)."
#define TX_ERR_WIFI_PASS    "Déjala vacía si la red es abierta, o usa de 8 a 63 caracteres sin acentos ni ñ."
#define TX_ERR_MQTT_HOST    "Escribe un nombre (letras, números, . y -) o una dirección IP, hasta 63 caracteres."
#define TX_ERR_MQTT_PORT    "Escribe un número entre 1 y 65535."
#define TX_ERR_MQTT_USER    "Hasta 64 caracteres."
#define TX_ERR_MQTT_PASS    "Hasta 64 caracteres."
#define TX_ERR_ID           "De 1 a 32 caracteres: minúsculas, números, - y _."
