# L1 sht41 (FSD §8). sht41_trama.c es un núcleo puro (también en tests/host);
# sht41.c es el adaptador I²C.
idf_component_register(SRCS "sht41_trama.c" "sht41.c"
                       INCLUDE_DIRS "include"
                       REQUIRES esp_common
                       PRIV_REQUIRES esp_driver_i2c log freertos)
