# L2 ota (FSD §7, §9.3, §12). ota_politica.c y ota_diag.c son núcleos puros (también en tests/host).
idf_component_register(SRCS "ota_politica.c" "ota_diag.c" INCLUDE_DIRS "include")
