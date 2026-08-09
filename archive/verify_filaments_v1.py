#!/usr/bin/env python3
"""verify_filaments.py — READ-ONLY. Compara filaments.yaml vs JSON en disco."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from orca_paths import preset_dir
try:
    import yaml
except ImportError:
    sys.exit("pip3 install -r requirements.txt")

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
ALIAS = {
    "Elegoo PLA @Kobra 2 Neo": "Elegoo PLA Calibrated @Kobra 2 Neo",
    "Elegoo TPU 95A Black @Kobra 2 Neo": "Elegoo TPU 95A Calibrated @Kobra 2 Neo",
}

d = preset_dir("filament")
y = yaml.safe_load(open("filaments.yaml"))
print(f"Comparando filaments.yaml  vs  {d}\n")
total = 0
for fil in y["filaments"]:
    name = fil["name"]
    disk_name = ALIAS.get(name, name)
    p = d / f"{disk_name}.json"
    print(f"> {name}")
    if not p.exists():
        print(f"   NO existe en disco: {disk_name}.json\n"); continue
    print(f"   comparando contra: {disk_name}.json")
    j = json.loads(p.read_text())
    diffs = []
    for ykey, jkey in MAP.items():
        v = j.get(jkey)
        v = v[0] if isinstance(v, list) and v else v
        if v is None:
            diffs.append((ykey, str(fil["settings"][ykey]), "<heredado>")); continue
        if str(fil["settings"][ykey]) != str(v):
            diffs.append((ykey, str(fil["settings"][ykey]), str(v)))
    print(f"   inherits: {j.get('inherits','<ninguno>')}")
    cpc = j.get("compatible_prints_condition")
    if cpc: print(f"   blindaje: {cpc}")
    if not diffs:
        print("   OK - YAML y disco coinciden en los 14 campos\n")
    else:
        print(f"   {len(diffs)} divergencia(s):")
        print(f"      {'campo':<26}{'YAML':>12}{'DISCO':>14}")
        for k, a, b in diffs:
            print(f"      {k:<26}{a:>12}{b:>14}")
        print()
        total += len(diffs)
print("Sin divergencias." if total == 0 else f"{total} divergencias en total.")
