# Nivel host: núcleos puros compilados con el compilador nativo, sin ESP-IDF
# (docs/Method/standards/testing.md). /build añade un test por requisito.
cmake_minimum_required(VERSION 3.22)
project(nodo_clima_host_tests C)
enable_testing()

# Comprueba que el nivel host funciona; no verifica ningún requisito del FSD.
add_executable(tier_smoke tier_smoke.c)
add_test(NAME tier_smoke COMMAND tier_smoke)
