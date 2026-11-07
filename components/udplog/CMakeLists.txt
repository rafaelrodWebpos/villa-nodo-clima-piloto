# L0 udplog (FSD §18.1). udplog_lineas.c, udplog_escritores.c y udplog_envio.c son núcleos puros (también en tests/host);
# udplog.c es el adaptador, que solo se compila con CONFIG_NODO_UDP_LOG=y.
idf_component_register(SRCS "udplog_lineas.c" "udplog_escritores.c" "udplog_envio.c" "udplog.c"
                       INCLUDE_DIRS "include"
                       PRIV_REQUIRES esp_event esp_netif esp_wifi esp_timer lwip log freertos)
