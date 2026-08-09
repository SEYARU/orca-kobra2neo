#!/usr/bin/env python3
"""
verify_filaments.py — READ-ONLY
Compara filaments.yaml contra los perfiles reales de OrcaSlicer, RESOLVIENDO
la cadena de herencia y normalizando números.

Por qué importa: un campo ausente en el JSON de usuario no es una
divergencia — se hereda del base. Y '1.0' vs '1' es el mismo número.
Sin normalizar ambas cosas el script reporta falsos positivos y deja de
ser confiable.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from orca_paths import ORCA_ROOT, preset_dir
try:
    import yaml
except ImportError:
    sys.exit("pip3 install -r requirements.txt")

SYSTEM = ORCA_ROOT / "system"

MAP = {
    "nozzle_temp": "nozzle_temperature",
    "first_layer_temp": "nozzle_temperature_initial_layer",
    "bed_temp": "hot_plate_temp",
    "first_layer_bed": "hot_plate_temp_initial_layer",
    "flow_ratio": "filament_flow_ratio",
    "max_volumetric_speed": "filament_max_volumetric_speed",
    "retraction": "filament_retraction_length",
    "retraction_speed": "filament_retraction_speed",
    "z_hop": "filament_z_hop",
    "fan_speed": "fan_max_speed",
    "disable_fan_first_layers": "close_fan_the_first_x_layers",
    "min_layer_time": "slow_down_layer_time",
    "min_print_speed": "slow_down_min_speed",
    "pressure_advance": "pressure_advance",
}

# Nombres unificados el 2026-08-09: el disco ahora usa los mismos nombres
# que filaments.yaml. Los antiguos "Calibrated" estan en _retirados/.
# Si algun dia vuelve a haber desalineamiento, mapealo aqui.
ALIAS = {}


def index_system():
    idx = {}
    if SYSTEM.is_dir():
        for f in SYSTEM.glob("*/filament/*.json"):
            idx.setdefault(f.stem, f)
    return idx


def chain(path, idx, limit=12):
    out, cur, name, seen = [], path, path.stem, set()
    for _ in range(limit):
        if cur is None or name in seen:
            break
        seen.add(name)
        try:
            data = json.loads(cur.read_text())
        except Exception:
            break
        out.append((name, data))
        parent = data.get("inherits")
        if not parent:
            break
        name, cur = parent, idx.get(parent)
    return out


def flat(v):
    return v[0] if isinstance(v, list) and v else v


def effective(ch, key):
    """Primer valor encontrado subiendo la cadena, y de dónde viene."""
    for n, d in ch:
        if key in d:
            return flat(d[key]), n
    return None, None


def same(a, b):
    """1.0 == 1. Si no son numéricos, compara texto."""
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return str(a) == str(b)


def main():
    idx = index_system()
    d = preset_dir("filament")
    y = yaml.safe_load(open("filaments.yaml"))

    print(f"Comparando filaments.yaml  vs  {d}")
    print(f"Perfiles de sistema indexados: {len(idx)}\n")

    real = 0
    for fil in y["filaments"]:
        name = fil["name"]
        disk = ALIAS.get(name, name)
        p = d / f"{disk}.json"
        print(f"> {name}")
        if not p.exists():
            print(f"   FALTA en disco: {disk}.json\n")
            real += 1
            continue
        if disk != name:
            print(f"   alias -> {disk}.json")

        ch = chain(p, idx)
        j = ch[0][1] if ch else {}
        print(f"   inherits: {j.get('inherits','<ninguno>')}   (cadena: {len(ch)} niveles)")
        if j.get("compatible_prints_condition"):
            print(f"   blindaje: {j['compatible_prints_condition']}")

        diffs, inherited = [], 0
        for ykey, jkey in MAP.items():
            want = fil["settings"][ykey]
            got, src = effective(ch, jkey)
            if got is None:
                diffs.append((ykey, str(want), "<sin definir>", "?"))
            elif not same(want, got):
                diffs.append((ykey, str(want), str(got), src))
            elif src != ch[0][0]:
                inherited += 1

        if not diffs:
            extra = f"  ({inherited} heredado(s) del base, valor correcto)" if inherited else ""
            print(f"   OK - los 14 campos coinciden{extra}\n")
        else:
            real += len(diffs)
            print(f"   {len(diffs)} DIVERGENCIA(S) REAL(ES):")
            print(f"      {'campo':<24}{'YAML':>10}{'EFECTIVO':>12}   origen")
            for k, a, b, s in diffs:
                print(f"      {k:<24}{a:>10}{b:>12}   {s}")
            print()

    if real == 0:
        print("OK - filaments.yaml es fiel al disco. Generar es seguro.")
    else:
        print(f"{real} divergencia(s) real(es). El DISCO gana: corrige el YAML antes de generar.")
    return 0 if real == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
