# Diagnóstico de TC-CFG-02 — un corte de alimentación (2026-11-06)

- DUT en SLOT1 con la imagen 0.0.0-9bcc519-bench, configurado contra un AP desechable ya apagado (T09/T10).
- `diag_corte.py` muestrea a 1 Hz el slot (`/api/devices`), la última línea del buffer serie y, al final, el log de actividad; el propietario hizo un corte al aviso del banco.
- `diag_corte.jsonl`: `t` en segundos desde el inicio; `ultima` = (ts de la línea en el banco − t0, uptime del DUT en s, texto). MACs redactadas.
- Resultado: slot `absent` a t = 531 s («Process died»), `present` a 545,6 s, proxy nuevo a 547,7 s; primera línea capturada `I (659) main_task: Returned from app_main()`: boot:, cfg: y con: ARRANQUE (≈ 0,65 s) se pierden (CR-TB-10).
- Log de actividad del banco: aviso 19:06:58, USB remove 19:15:39, USB add 19:15:53, «Human confirmed» 19:15:56; el script acabó en `CommandTimeout` (CR-TB-11), así que no llegó a escribir su evento «fin».
