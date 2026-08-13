#!/usr/bin/env python3
"""
check_petg_base.py — READ-ONLY
Busca un base de filamento PETG especifico para la Kobra 2 Neo.

POR QUE IMPORTA
    Heredar de un generico de marca ("Anycubic Generic PETG") hace que
    OrcaSlicer registre el perfil pero lo FILTRE del dropdown: el base no
    declara compatibilidad con ninguna Kobra. Es el fallo silencioso
    documentado en el README.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from orca_paths import ORCA_ROOT

SYSTEM = ORCA_ROOT / "system"

print("Bases de filamento que mencionan PETG:\n")
hits = []
for f in sorted(SYSTEM.glob("*/filament/*.json")):
    n = f.stem
    if "petg" not in n.lower():
        continue
    try:
        d = json.loads(f.read_text())
    except Exception:
        continue
    cp = d.get("compatible_printers", [])
    cpc = d.get("compatible_printers_condition", "")
    kobra2neo = any("Kobra 2 Neo" in str(x) for x in (cp if isinstance(cp, list) else [cp]))
    marca = "  <-- ESPECIFICO KOBRA 2 NEO" if ("Kobra 2 Neo" in n or kobra2neo) else ""
    hits.append((n, f.parts[-3], len(cp) if isinstance(cp, list) else 0, marca))
    print(f"   [{f.parts[-3]:<10}] {n}{marca}")
    if cp:
        muestra = [x for x in cp if "Kobra" in str(x)][:3]
        if muestra:
            print(f"                 compatible con: {muestra}")
    if cpc:
        print(f"                 condicion: {cpc[:70]}")

if not hits:
    print("   NINGUNO. Habra que heredar del base de PLA especifico,")
    print("   igual que hace el TPU (se hereda la COMPATIBILIDAD, no el material).")

print("\n" + "="*70)
print("Base que usan hoy PLA y TPU (referencia):")
ref = "Anycubic PLA @Anycubic Kobra 2 Neo 0.4 nozzle"
p = list(SYSTEM.glob(f"*/filament/{ref}.json"))
if p:
    d = json.loads(p[0].read_text())
    cp = d.get("compatible_printers", [])
    print(f"   {ref}")
    print(f"   compatible_printers: {cp if cp else '<vacio>'}")
    print(f"   filament_type      : {d.get('filament_type','<hereda>')}")
else:
    print("   NO ENCONTRADO (?)")
