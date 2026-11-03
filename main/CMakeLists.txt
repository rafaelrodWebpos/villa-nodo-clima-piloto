# Raíz de composición. Cada componente se añade con la fase que lo usa
# (docs/Method/project/arquitectura.md); nada especulativo en PRIV_REQUIRES.
idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES esp_app_format app_update esp_hw_support esp_system
                                     esp_event esp_netif esp_wifi nvs_flash
                                     identidad conectividad)
