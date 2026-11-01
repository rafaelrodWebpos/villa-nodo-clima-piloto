# Firmware de prueba de C-HW-04/05 (FSD §18 E12) y del cableado del SHT41
# (agenda de depuración, filas 2 y 3). No es el firmware del nodo: la CI no lo
# publica y su configuración del bus no cuenta para la revisión de C-HW-04/05.
cmake_minimum_required(VERSION 3.22)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(i2c_probe)
