# Nivel host: núcleos puros compilados con el compilador nativo, sin ESP-IDF
# (docs/Method/standards/testing.md). /build añade un test por requisito.
cmake_minimum_required(VERSION 3.22)
project(nodo_clima_host_tests C)
enable_testing()
set(COMP ${CMAKE_CURRENT_SOURCE_DIR}/../../components)
add_compile_options(-Wall -Wextra -Werror)

# Comprueba que el nivel host funciona; no verifica ningún requisito del FSD.
add_executable(tier_smoke tier_smoke.c)
add_test(NAME tier_smoke COMMAND tier_smoke)

# TC-ID-01 · FR-ID-01
add_executable(test_identidad test_identidad.c ${COMP}/identidad/identidad.c)
target_include_directories(test_identidad PRIVATE ${COMP}/identidad/include)
add_test(NAME TC-ID-01 COMMAND test_identidad)

# TC-CON-01 · T01, T02 (filas de la tabla §6.3 implementadas)
add_executable(test_conectividad test_conectividad.c ${COMP}/conectividad/conectividad.c)
target_include_directories(test_conectividad PRIVATE ${COMP}/conectividad/include)
add_test(NAME TC-CON-01 COMMAND test_conectividad)

# TC-POR-01 · FR-POR-03 (generador del formulario)
add_executable(test_portal_form test_portal_form.c ${COMP}/portal/portal_form.c)
target_include_directories(test_portal_form PRIVATE ${COMP}/portal/include)
add_test(NAME TC-POR-01 COMMAND test_portal_form)

# TC-POR-03 · FR-POR-04 (validador de §17)
add_executable(test_portal_validar test_portal_validar.c ${COMP}/portal/portal_validar.c ${COMP}/portal/portal_form.c)
target_include_directories(test_portal_validar PRIVATE ${COMP}/portal/include)
add_test(NAME TC-POR-03 COMMAND test_portal_validar)

# TC-POR-04 · FR-POR-04 (respuesta a un envío inválido)
add_executable(test_portal_envio test_portal_envio.c ${COMP}/portal/portal_urlenc.c ${COMP}/portal/portal_validar.c ${COMP}/portal/portal_form.c)
target_include_directories(test_portal_envio PRIVATE ${COMP}/portal/include)
add_test(NAME TC-POR-04 COMMAND test_portal_envio)

# TC-POR-06 · FR-POR-02 (redirección y DNS del portal cautivo)
add_executable(test_portal_cautivo test_portal_cautivo.c ${COMP}/portal/portal_cautivo.c)
target_include_directories(test_portal_cautivo PRIVATE ${COMP}/portal/include)
add_test(NAME TC-POR-06 COMMAND test_portal_cautivo)

# TC-POR-10 · FR-POR-06 (los datos del formulario se guardan tal cual)
add_executable(test_portal_config test_portal_config.c ${COMP}/portal/portal_config.c ${COMP}/portal/portal_validar.c ${COMP}/portal/portal_form.c)
target_include_directories(test_portal_config PRIVATE ${COMP}/portal/include)
add_test(NAME TC-POR-10 COMMAND test_portal_config)

# TC-SEC-02 · FR-SEC-03 (el log de páginas no escribe la consulta de la URL)
add_executable(test_log_ruta test_log_ruta.c ${COMP}/portal/portal_cautivo.c)
target_include_directories(test_log_ruta PRIVATE ${COMP}/portal/include)
add_test(NAME TC-SEC-02 COMMAND test_log_ruta)

# TC-LOG-02 · FR-LOG-02 (ensamblado de líneas del log UDP)
add_executable(test_udplog_lineas test_udplog_lineas.c ${COMP}/udplog/udplog_lineas.c)
target_include_directories(test_udplog_lineas PRIVATE ${COMP}/udplog/include)
add_test(NAME TC-LOG-02 COMMAND test_udplog_lineas)
