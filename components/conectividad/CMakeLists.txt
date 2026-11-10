# L2 conectividad (FSD §6). Tabla pura; también la compila tests/host.
idf_component_register(SRCS "conectividad.c" "conectividad_backoff.c" "conectividad_sta.c" INCLUDE_DIRS "include")
