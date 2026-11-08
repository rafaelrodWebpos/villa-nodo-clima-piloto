# FORK-01 — Salida del AP: valores por defecto y reinicio

- /api/info: build=8966260, capabilities=['bench-ap-internet', 'bench-sntp-block']

- Estado inicial
- Cuerpos inválidos: {"enabled": "false"}, {"enabled": 1}, {} → 400 y sin cambios
- Encender la salida (sin AP)
- Bloquear SNTP
- Levantar un AP de prueba y pararlo: ap_stop devuelve todo a apagado
- Encender y apagar: rules_ok en cada paso

## Resultado

- inicial: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- POST {"enabled": "false"} → 400: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- POST {"enabled": 1} → 400: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- POST {} → 400: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- encendida: internet=True sntp_blocked=False lan_blocked=True rules_ok=True reglas=15
- sntp bloqueado: internet=True sntp_blocked=True lan_blocked=True rules_ok=True reglas=16
- tras ap_start: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- tras ap_stop: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- internet True: internet=True sntp_blocked=False lan_blocked=True rules_ok=True reglas=15
- internet False: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2
- internet True: internet=True sntp_blocked=False lan_blocked=True rules_ok=True reglas=15
- internet False: internet=False sntp_blocked=False lan_blocked=True rules_ok=True reglas=2

Reglas con la salida encendida y SNTP bloqueado:

    -N HARNESS_AP_FWD
    -A HARNESS_AP_FWD -o wlan0 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
    -A HARNESS_AP_FWD -o wlan0 -j DROP
    -A HARNESS_AP_FWD -p udp -m udp --dport 123 -j DROP
    -A HARNESS_AP_FWD -d 192.168.4.0/24 -j ACCEPT
    -A HARNESS_AP_FWD -d 0.0.0.0/8 -j DROP
    -A HARNESS_AP_FWD -d 10.0.0.0/8 -j DROP
    -A HARNESS_AP_FWD -d 100.64.0.0/10 -j DROP
    -A HARNESS_AP_FWD -d 127.0.0.0/8 -j DROP
    -A HARNESS_AP_FWD -d 169.254.0.0/16 -j DROP
    -A HARNESS_AP_FWD -d 172.16.0.0/12 -j DROP
    -A HARNESS_AP_FWD -d 192.168.0.0/16 -j DROP
    -A HARNESS_AP_FWD -d 224.0.0.0/4 -j DROP
    -A HARNESS_AP_FWD -d 240.0.0.0/4 -j DROP
    -A HARNESS_AP_FWD -o eth0 -j ACCEPT
    -A HARNESS_AP_FWD -j DROP

**Resultado: PASS** — capacidades reportadas; apagado por defecto y tras ap_stop; rangos privados cortados; SNTP antes de cualquier ACCEPT; cuerpos no booleanos → 400; rules_ok en todos los pasos
