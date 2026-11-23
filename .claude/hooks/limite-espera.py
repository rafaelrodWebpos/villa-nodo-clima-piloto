#!/usr/bin/env python3
"""Candado contra esperas sin límite (H-62, capa 2).

Hook PreToolUse de Claude Code para la herramienta Bash. Bloquea:
  1. Un comando en segundo plano (run_in_background) que espera (bucle until/while con
     sleep, `docker wait` o `tail --pid`) sin envolverlo en `timeout N` con N <= 600 s.
     Excepción (decisión del propietario, 2026-11-23): una espera larga de hasta 93600 s
     (26 h) solo con una de estas dos formas exactas, siempre con timeout:
       timeout N docker wait <contenedor>
       timeout N bash -c 'while kill -0 <pid> [2>/dev/null]; do sleep 60; done'
     Cualquier otra espera del mismo comando sigue limitada a 600 s.
  2. `gh run list -c <hash corto>`: con el hash abreviado no devuelve nada y la
     espera nunca termina (atasco del 2026-11-07). Hay que usar el hash completo
     (40 caracteres), por ejemplo $(git rev-parse <hash>).
Si no hay nada que bloquear, no imprime nada y deja pasar el comando.
"""
import json
import re
import sys

LIMITE_S = 600
LIMITE_LARGO_S = 93600
# Las dos esperas largas permitidas, con su timeout (grupo 1 = segundos)
LARGA = re.compile(
    r"\btimeout\s+(\d+)\s+(?:docker\s+wait\s+[\w.-]+"
    r"|bash\s+-c\s+(['\"])\s*while\s+kill\s+-0\s+\d+(?:\s+2>\s*/dev/null)?\s*;\s*do\s+sleep\s+60\s*;\s*done\s*\2)")


def es_espera(cmd):
    bucle = re.search(r"\b(until|while)\b", cmd) and re.search(r"\bsleep\b", cmd)
    return bool(bucle or re.search(r"\bdocker\s+wait\b", cmd) or re.search(r"\btail\b[^|;&\n]*--pid", cmd))


def denegar(motivo):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": motivo,
        }
    }))
    sys.exit(0)


def main():
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return
    if datos.get("tool_name") != "Bash":
        return
    entrada = datos.get("tool_input") or {}
    cmd = entrada.get("command") or ""

    for m in re.finditer(r"gh\s+run\s+(?:list|watch)\b[^|;&\n]*?(?:-c|--commit)[\s=]+([0-9a-fA-F]+)\b", cmd):
        if len(m.group(1)) != 40:
            denegar("H-62: `gh run list -c` necesita el hash COMPLETO de 40 caracteres; con el corto no "
                    "devuelve nada y la espera nunca termina. Usa $(git rev-parse <hash>).")

    if entrada.get("run_in_background"):
        largas = list(LARGA.finditer(cmd))
        if largas and all(int(m.group(1)) <= LIMITE_LARGO_S for m in largas):
            resto = LARGA.sub(" ", cmd)
            if not es_espera(resto):
                return          # solo esperas largas permitidas, cada una con su timeout
            cmd = resto         # lo demás se juzga con el límite corto
        if es_espera(cmd):
            t = re.search(r"\btimeout\s+(?:-[-\w=]+\s+)*(\d+)(s|m)?\b", cmd)
            seg = None
            if t:
                seg = int(t.group(1)) * (60 if t.group(2) == "m" else 1)
            if seg is None or seg > LIMITE_S:
                denegar(f"H-62: toda espera en segundo plano necesita límite. Envuelve el bucle en "
                        f"`timeout {LIMITE_S} bash -c '...'` (máximo {LIMITE_S} s) y, si se agota, "
                        f"compruébalo tú directamente y avisa al propietario. Una espera larga (hasta "
                        f"{LIMITE_LARGO_S} s) solo con `timeout N docker wait <contenedor>` o "
                        f"`timeout N bash -c 'while kill -0 <pid>; do sleep 60; done'`.")


if __name__ == "__main__":
    main()
