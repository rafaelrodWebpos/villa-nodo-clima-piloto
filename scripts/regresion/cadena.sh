#!/usr/bin/env bash
# Regresión con ESP-IDF 6.0.3 (testing/regresion-6.0.3.md): una sola cadena desacoplada en el SLOT1.
# Uso, desde la raíz del repo y solo tras el aviso del propietario de que el banco está libre:
#   scripts/regresion/cadena.sh <run-id del build de banco> <run-id del build de producción> <sha7> [--con-wdt]
# Un contenedor corre las tandas A–F una tras otra, sin -x (si una prueba falla, sigue). La tanda 0
# (TC-WDT-01, 24 h) solo con --con-wdt: el propietario la dejó fuera de la regresión 6.0.3 (2026-11-20).
# Cada tanda deja su salida en test-results/cadena-<fecha>/<tanda>.log. TESTBENCH_URL y
# TESTBENCH_TOKEN salen del .env (nunca se versionan). Estado: docker logs cadena.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
set -a; . ./.env; set +a
RUN_BANCO=$1; RUN_PROD=$2; V=$3; CON_WDT=${4:-}
FW=${TMPDIR:-/tmp}/cadena-fw-$V
mkdir -p "$FW/banco" "$FW/prod"
[ -f "$FW/banco/firmware_v0.0.0-$V-bench.bin" ] || gh run download "$RUN_BANCO" -n "firmware-v0.0.0-$V-bench" -D "$FW/banco" >/dev/null
[ -f "$FW/prod/firmware_v0.0.0-$V.bin" ] || gh run download "$RUN_PROD" -n "firmware-v0.0.0-$V" -D "$FW/prod" >/dev/null
OUT=test-results/cadena-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$OUT"

B=tests/bench
T0=""
[ "$CON_WDT" = "--con-wdt" ] && T0="$B/test_wdt.py::test_tc_wdt_01_24h_stability"
TA="$B/test_jrn01.py::test_jrn_01_0_flash_ci_image $B/test_jrn01.py::test_jrn_01_1_portal_without_config
 $B/test_jrn01.py::test_jrn_01_2_provision $B/test_jrn01.py::test_jrn_01_3_wifi_and_udp_log
 $B/test_jrn01.py::test_jrn_01_4_broker_and_status $B/test_jrn01.py::test_jrn_01_5_home_assistant_discovery
 $B/test_bench_plus.py::test_jrn_01_6_sntp_and_measures $B/test_por.py::test_tc_por_02_get_form
 $B/test_por.py::test_tc_por_05_invalid_submit $B/test_por.py::test_tc_por_07_captive_redirects
 $B/test_por.py::test_tc_por_09_wrong_password $B/test_por.py::test_tc_por_11_no_portal_when_configured
 $B/test_seguridad.py::test_tc_por_12_portal_closes_after_10_min $B/test_con.py::test_tc_con_07_busy_while_validating
 $B/test_seguridad.py::test_tc_con_14_open_twin_rejected $B/test_hw.py::test_tc_hw_02_chip_reading
 $B/test_hw.py::test_tc_hw_03_boots_without_psram"
TB="$B/test_con.py::test_tc_con_03_wifi_backoff $B/test_con.py::test_tc_con_06_never_portal
 $B/test_mqtt.py::test_tc_con_08_broker_outage $B/test_mqtt.py::test_tc_con_09_wifi_loss_connecting_broker
 $B/test_mqtt.py::test_tc_con_10_wifi_loss_operativo $B/test_mqtt.py::test_tc_mqtt_03_connect_order_and_retain
 $B/test_villa2.py::test_tc_mqtt_05_broker_authentication $B/test_med.py::test_tc_med_01_period_60_s
 $B/test_med.py::test_tc_med_02_cycle_without_broker $B/test_bench_plus.py::test_tc_med_06_reconnect_publishes_latest_only
 $B/test_log.py::test_tc_log_03_udp_log_to_nowhere $B/test_villa2.py::test_tc_log_08_udp_log_unicast_only"
TC="$B/test_time.py::test_tc_time_05_publish_without_time $B/test_time.py::test_tc_time_06_sntp_retry_without_time
 $B/test_villa2.py::test_tc_time_08_reboot_without_sntp $B/test_villa2.py::test_tc_wdt_02_task_watchdog"
TD="$B/test_jrn02.py::test_jrn_02_1_ota_to_b1_and_b2 $B/test_jrn02.py::test_jrn_02_2_rollback_when_new_image_never_operative
 $B/test_ota.py::test_tc_ota_06_rejections $B/test_ota.py::test_tc_ota_07_retained_command_ignored
 $B/test_ota.py::test_tc_ota_08_missing_asset_http_error $B/test_ota.py::test_tc_ota_09_untrusted_certificate_tls_error
 $B/test_jrn02.py::test_tc_ota_10_bad_images $B/test_jrn02.py::test_tc_ota_11_ap_lost_during_download
 $B/test_jrn02.py::test_tc_ota_12_busy_during_download $B/test_jrn02.py::test_nfr_ota_01_measurement_period_during_download
 $B/test_jrn02.py::test_tc_ota_17_abort_slow_download_then_new_command"
TE="$B/test_mqtt.py::test_tc_con_15_return_order_after_outage $B/test_con_largo.py::test_tc_con_11_ap_off_60_min $B/test_con_largo.py::test_tc_con_12_broker_off_60_min
 $B/test_bench_plus.py::test_tc_time_04_resync_failure_keeps_time"
TF="$B/test_villa2.py::test_tc_log_04_no_udp_log_in_production $B/test_ota.py::test_tc_ota_14_production_rejects_test_prerelease"

# Dentro del contenedor: las variables llegan por -e; las comillas simples impiden que este shell las expanda
CADENA='
PY="/opt/bench-venv/bin/python -m pytest -rA --tb=short -p no:cacheprovider"   # --tb=short: sin variables locales (cabeceras con el token, 2026-11-21)
tanda() { echo "== tanda $1 $(date -u +%FT%TZ)"; }
if [ -n "$T0" ]; then tanda 0; $PY $T0 --firmware-dir $FW/banco > $OUT/0-wdt.log 2>&1 || true; fi
tanda A; $PY $TA --firmware-dir $FW/banco > $OUT/A.log 2>&1 || true
tanda B; $PY $TB --firmware-dir $FW/banco > $OUT/B.log 2>&1 || true
tanda C; $PY $TC --firmware-dir $FW/banco > $OUT/C.log 2>&1 || true
tanda D; $PY $TD --firmware-dir $FW/banco > $OUT/D.log 2>&1 || true
tanda E; $PY $TE --firmware-dir $FW/banco > $OUT/E.log 2>&1 || true
tanda F; $PY tests/bench -m journey --firmware-dir $FW/prod > $OUT/F-journey.log 2>&1 || true
$PY $TF --firmware-dir $FW/prod > $OUT/F-produccion.log 2>&1 || true
echo "== fin $(date -u +%FT%TZ)"
'
docker rm -f cadena >/dev/null 2>&1 || true
docker run -d --name cadena --network=host -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e TESTBENCH_URL -e TESTBENCH_TOKEN -e OUT="$OUT" -e FW="$FW" \
  -e T0="$T0" -e TA="$TA" -e TB="$TB" -e TC="$TC" -e TD="$TD" -e TE="$TE" -e TF="$TF" \
  -v "$PWD:$PWD" -v "$FW:$FW" -w "$PWD" nodo-clima-piloto-dev:latest bash -c "$CADENA" >/dev/null
echo "cadena lanzada $(date '+%F %T'); salida en $OUT; estado: docker logs cadena"
