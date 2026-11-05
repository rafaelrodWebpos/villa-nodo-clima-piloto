# L0 udplog (FSD §18.1). udplog_lineas.c es un núcleo puro (también en tests/host);
# udplog.c es el adaptador, que solo se compila con CONFIG_NODO_UDP_LOG=y.
idf_component_register(SRCS "udplog_lineas.c" "udplog.c"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES esp_event esp_netif esp_wifi lwip log freertos)
