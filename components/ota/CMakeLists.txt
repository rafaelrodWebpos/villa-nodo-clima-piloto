# L2 ota (FSD §7, §9.3, §12). ota_politica.c y ota_diag.c son núcleos puros (también en
# tests/host); ota_descarga.c es el adaptador de ESP-IDF (esp_https_ota).
idf_component_register(SRCS "ota_politica.c" "ota_diag.c" "ota_descarga.c"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES esp_https_ota esp_http_client mbedtls app_update esp-tls freertos log)
