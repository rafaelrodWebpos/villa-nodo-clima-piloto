# Raíz de composición. Cada componente se añade con la fase que lo usa
# (docs/Method/project/arquitectura.md); nada especulativo en PRIV_REQUIRES.
idf_component_register(SRCS "main.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES esp_app_format)
