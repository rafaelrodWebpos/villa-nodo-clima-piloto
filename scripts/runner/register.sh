#!/usr/bin/env bash
# Registra el runner self-hosted del job release-verify y lo mantiene vivo.
#
# QUÉ SIGNIFICA REGISTRARLO: este contenedor acepta y ejecuta código de
# workflows de rafaelrodWebpos/villa-nodo-clima-piloto, que después mueve el
# testbench físicamente. Es una autorización permanente, como el propio tag de
# release, y solo la concede el propietario. Por eso no se ejecuta solo.
#
# Uso (dentro del devcontainer, con `gh` autenticado como el propietario):
#   scripts/runner/register.sh
#
# Registro por repositorio, etiquetas self-hosted,testbench, efímero (un job
# por registro) y en bucle de reinicio. El workflow solo lo usa con tags
# v*.*.* del propietario.
set -euo pipefail

REPO="rafaelrodWebpos/villa-nodo-clima-piloto"
RUNNER_DIR=/opt/actions-runner
NAME="nodo-clima-$(hostname)"

while true; do
  TOKEN=$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq .token)
  sudo -u runner "$RUNNER_DIR/config.sh" --unattended --ephemeral --replace \
       --url "https://github.com/$REPO" --token "$TOKEN" \
       --name "$NAME" --labels self-hosted,testbench --work _work
  # El banco villa-2 exige el token en /api/* (S6-01): sin él, el journey de verify falla
  sudo -u runner --preserve-env=TESTBENCH_URL,TESTBENCH_TOKEN "$RUNNER_DIR/run.sh" || true
  sleep 5
done
