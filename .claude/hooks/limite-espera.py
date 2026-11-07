#!/usr/bin/env python3
"""Candado contra esperas sin límite (H-62, capa 2).

Hook PreToolUse de Claude Code para la herramienta Bash. Bloquea:
  1. Un comando en segundo plano (run_in_background) que espera en un bucle
     (until/while ... sleep) sin envolverlo en `timeout N` con N <= 600 s.
  2. `gh run list -c <hash corto>`: con el hash abreviado no devuelve nada y la
     espera nunca termina (atasco del 2026-11-07). Hay que usar el hash completo
     (40 caracteres), por ejemplo $(git rev-parse <hash>).
Si no hay nada que bloquear, no imprime nada y deja pasar el comando.
"""
import json
import re
import sys

LIMITE_S = 600


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
        bucle = re.search(r"\b(until|while)\b", cmd) and re.search(r"\bsleep\b", cmd)
        if bucle:
            t = re.search(r"\btimeout\s+(?:-[-\w=]+\s+)*(\d+)(s|m)?\b", cmd)
            seg = None
            if t:
                seg = int(t.group(1)) * (60 if t.group(2) == "m" else 1)
            if seg is None or seg > LIMITE_S:
                denegar(f"H-62: toda espera en segundo plano necesita límite. Envuelve el bucle en "
                        f"`timeout {LIMITE_S} bash -c '...'` (máximo {LIMITE_S} s) y, si se agota, "
                        f"compruébalo tú directamente y avisa al propietario.")


if __name__ == "__main__":
    main()
