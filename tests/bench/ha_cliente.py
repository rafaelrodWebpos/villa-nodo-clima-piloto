"""Cliente del Home Assistant de prueba (capacidad home-assistant-test, decisión H-52).

La instancia la levanta en la laptop `scripts/ha/ha_prueba.py up`, que deja en
`.ha-prueba.env` (no versionado) HA_URL, HA_CLIENT_ID y HA_REFRESH_TOKEN. Sin ese
fichero, los tests que lo necesitan quedan en not done. Solo biblioteca estándar.
"""
import json
import pathlib
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

import pytest

ENV = pathlib.Path(__file__).resolve().parents[2] / ".ha-prueba.env"


class HomeAssistant:
    def __init__(self):
        if not ENV.exists():
            pytest.skip("not done: no hay Home Assistant de prueba (scripts/ha/ha_prueba.py up)")
        cfg = dict(ln.split("=", 1) for ln in ENV.read_text().split() if "=" in ln)
        self.url, self.client_id, self._refresh = cfg["HA_URL"], cfg["HA_CLIENT_ID"], cfg["HA_REFRESH_TOKEN"]
        self._token, self._caduca = None, 0.0
        try:
            self.version = self.get("/api/config").get("version")
        except (urllib.error.URLError, OSError) as e:
            pytest.skip(f"not done: el Home Assistant de prueba no responde ({type(e).__name__})")

    def _pedir(self, metodo, ruta, datos=None, form=False, auth=True, timeout=20):
        cab, cuerpo = {}, None
        if datos is not None:
            cuerpo = urllib.parse.urlencode(datos).encode() if form else json.dumps(datos).encode()
            cab["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
        if auth:
            cab["Authorization"] = f"Bearer {self.token()}"
        req = urllib.request.Request(self.url + ruta, data=cuerpo, headers=cab, method=metodo)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            txt = r.read().decode()
        try:
            return json.loads(txt) if txt else {}
        except json.JSONDecodeError:
            return txt

    def token(self):
        if not self._token or time.time() > self._caduca:
            r = self._pedir("POST", "/auth/token", {"grant_type": "refresh_token", "refresh_token": self._refresh,
                                                     "client_id": self.client_id}, form=True, auth=False)
            self._token, self._caduca = r["access_token"], time.time() + r.get("expires_in", 1800) - 60
        return self._token

    def get(self, ruta):
        return self._pedir("GET", ruta)

    def post(self, ruta, datos):
        return self._pedir("POST", ruta, datos)

    def plantilla(self, tpl):
        return self._pedir("POST", "/api/template", {"template": tpl})

    def anadir_mqtt(self, host_banco, puerto=1883):
        """Integración MQTT contra el broker del banco (tiene que estar arrancado: el
        asistente comprueba la conexión). La dirección nunca va a la evidencia."""
        ip = socket.gethostbyname(host_banco)
        paso = self.post("/api/config/config_entries/flow", {"handler": "mqtt", "show_advanced_options": False})
        for _ in range(5):
            tipo = paso.get("type")
            if tipo == "create_entry":
                return paso["result"]["entry_id"] if isinstance(paso.get("result"), dict) else paso.get("result")
            if tipo == "abort":
                raise AssertionError(f"integración MQTT abortada: {paso.get('reason')}")
            if tipo == "menu":
                datos = {"next_step_id": "broker" if "broker" in paso.get("menu_options", []) else paso["menu_options"][0]}
            elif tipo == "form":
                if paso.get("errors"):
                    raise AssertionError(f"integración MQTT: {paso['errors']}")
                # 2026.10: protocolo y el bloque «other_settings» son obligatorios (TCP, sin TLS, §9.1)
                datos = {"broker": ip, "port": puerto, "protocol": "3.1.1",
                         "other_settings": {"set_client_cert": False, "set_ca_cert": "off", "transport": "tcp"}}
            else:
                raise AssertionError(f"paso inesperado del asistente MQTT: {tipo}")
            try:
                paso = self.post(f"/api/config/config_entries/flow/{paso['flow_id']}", datos)
            except urllib.error.HTTPError as e:
                raise AssertionError(f"integración MQTT: HTTP {e.code} {e.read().decode()[:200]}") from None
        raise AssertionError("el asistente MQTT no terminó en 5 pasos")

    def dispositivos_mqtt(self):
        """{device_id: {nombre, entidades: [{entity_id, unit, state}]}} de la integración MQTT."""
        tpl = ("{% set ns = namespace(d={}) %}{% for e in integration_entities('mqtt') %}"
               "{% set d = device_id(e) %}{% if d %}{% set ns.d = dict(ns.d, **{d: ns.d.get(d, []) + [e]}) %}"
               "{% endif %}{% endfor %}{{ ns.d | tojson }}")
        mapa = self.plantilla(tpl)
        mapa = json.loads(mapa) if isinstance(mapa, str) else mapa
        out = {}
        for dev, ents in mapa.items():
            nombre = self.plantilla(f"{{{{ device_attr('{dev}', 'name') }}}}")
            filas = []
            for e in ents:
                st = self.get(f"/api/states/{e}")
                filas.append({"entity_id": e, "state": st.get("state"),
                              "unit": st.get("attributes", {}).get("unit_of_measurement")})
            out[dev] = {"nombre": nombre, "entidades": filas}
        return out
