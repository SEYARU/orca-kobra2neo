#!/usr/bin/env python3
"""resolve_inherited.py — READ-ONLY. Resuelve valores efectivos via herencia."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from orca_paths import ORCA_ROOT, preset_dir

SYSTEM = ORCA_ROOT / "system"
CHECK = {
    "bed_temp": "hot_plate_temp",
    "first_layer_bed": "hot_plate_temp_initial_layer",
    "fan_speed": "fan_max_speed",
    "min_print_speed": "slow_down_min_speed",
    "flow_ratio": "filament_flow_ratio",
    "nozzle_temp": "nozzle_temperature",
}

def index_system():
    idx = {}
    if SYSTEM.is_dir():
        for f in SYSTEM.glob("*/filament/*.json"):
            idx.setdefault(f.stem, f)
    return idx

def chain(start_path, idx, limit=12):
    out, cur, name = [], start_path, start_path.stem
    seen = set()
    for _ in range(limit):
        if cur is None or name in seen: break
        seen.add(name)
        try:
            data = json.loads(cur.read_text())
        except Exception as e:
            out.append((f"{name} <ilegible: {e}>", {})); break
        out.append((name, data))
        parent = data.get("inherits")
        if not parent: break
        name = parent
        cur = idx.get(parent)
        if cur is None:
            out.append((f"{parent} <NO ENCONTRADO>", {})); break
    return out

def flat(v):
    return v[0] if isinstance(v, list) and v else v

def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "Elegoo PLA Calibrated @Kobra 2 Neo"
    idx = index_system()
    print(f"Perfiles de sistema indexados: {len(idx)}\n")
    p = preset_dir("filament") / f"{target}.json"
    if not p.exists(): sys.exit(f"No existe: {p}")
    ch = chain(p, idx)
    print("Cadena de herencia:")
    for i, (n, _) in enumerate(ch):
        print(f"   {'  ' * i}{'^- ' if i else ''}{n}")
    print()
    print(f"{'campo':<22}{'valor efectivo':>16}   proviene de")
    print("-" * 70)
    for ykey, jkey in CHECK.items():
        val, src = "<sin definir>", "-"
        for n, d in ch:
            if jkey in d:
                val, src = flat(d[jkey]), n; break
        print(f"{ykey:<22}{str(val):>16}   {src}")

if __name__ == "__main__":
    main()
