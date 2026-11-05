"""Carga testing/test-plan.yaml y comprueba lo mínimo para que el plan sea legible:
YAML válido, ids de test únicos y cada need declarado en capabilities. Un plan
roto pone la CI en rojo (petición del propietario, 2026-11-04)."""
import sys, yaml
try:
    p = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
except yaml.YAMLError as e:
    print("::error title=plan::testing/test-plan.yaml no carga:", str(e).replace("\n", " ")); sys.exit(1)
caps, tests = p["capabilities"], p["tests"]
ids = [t["id"] for t in tests]
dup = sorted({i for i in ids if ids.count(i) > 1})
undef = [(t["id"], n) for t in tests for n in t.get("needs", []) if n not in caps]
print(f"plan: {len(tests)} tests, {len(caps)} capacidades")
if dup or undef:
    print("::error title=plan::ids repetidos", dup, "needs sin capacidad", undef); sys.exit(1)
