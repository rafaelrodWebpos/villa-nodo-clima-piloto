# L1 portal (FSD §11). portal_form.c es un núcleo puro (también en tests/host);
# portal_http.c es el adaptador de ESP-IDF.
idf_component_register(SRCS "portal_origen.c" "portal_lectura.c" "portal_form.c" "portal_validar.c" "portal_urlenc.c" "portal_cautivo.c" "portal_config.c" "portal_http.c" "portal_dns.c"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES esp_http_server esp_timer lwip)
