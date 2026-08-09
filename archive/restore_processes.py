#!/usr/bin/env python3
"""
restore_processes.py
------------------------------------------------------------------------------
Restaura los process presets ORIGINALES y deriva "PLA Wood Default" a partir
del PLA real, no de valores inventados.

POR QUÉ
    generate_processes.py construye el JSON campo por campo y su builder NO
    contempla los parámetros de soporte (12) ni de scarf seam (7). Al
    regenerar, esos campos simplemente desaparecen. Además duplica el signo
    de porcentaje ('15%' -> '15%%') y sobrescribe velocidades medidas con
    los defaults del YAML.

    Mientras el builder no se extienda, los process presets NO deben
    regenerarse con ese script.

QUÉ HACE
    1. Restaura "PLA Default" y "TPU 95A Default" desde backups_process/
    2. Crea "PLA Wood Default" copiando el PLA restaurado y aplicando solo
       los overrides específicos del wood
    3. Conserva intactos soportes, scarf seam y todo lo demás

Uso:
    python3 restore_processes.py --dry-run
    python3 restore_processes.py
"""

import json
import glob
import shutil
import sys
from pathlib import Path
from datetime import datetime

ORCA = Path.home() / (
    "Library/Application Support/OrcaSlicer/user/"
    "ba9291fb-5260-4dc6-8ff3-0c3be79554dc/process"
)
BACKUPS = Path(__file__).parent / "backups_process"

# Backups previos a la primera regeneración de hoy
ORIGINALS = {
    "PLA Default @Kobra 2 Neo": "PLA Default @Kobra 2 Neo_20260731_1312*.json",
    "TPU 95A Default @Kobra 2 Neo": "TPU 95A Default @Kobra 2 Neo_20260731_1312*.json",
}

# Overrides del wood sobre el PLA real.
# Deliberadamente MÍNIMOS: solo lo que el material exige.
# La pared exterior del PLA ya está en 30, que es justo lo que quiere el
# wood, así que no se toca.
WOOD_OVERRIDES = {
    "inner_wall_speed": ["45"],        # desde 80
    "sparse_infill_speed": ["50"],     # desde 120
    "internal_solid_infill_speed": ["50"],
    "top_surface_speed": ["30"],       # desde 40
    "line_width": ["0.45"],            # extrusión más ancha: menos presión
    "outer_wall_line_width": ["0.45"],
}


def find_original(pattern):
    hits = sorted(glob.glob(str(BACKUPS / pattern)))
    return Path(hits[0]) if hits else None


def main():
    dry = "--dry-run" in sys.argv

    print("=" * 70)
    print("♻️  Restauración de process presets originales")
    print("=" * 70)

    if not ORCA.exists():
        print(f"❌ No existe {ORCA}")
        return 1
    if not BACKUPS.exists():
        print(f"❌ No existe {BACKUPS}")
        return 1

    # --- Localizar originales ---
    found = {}
    for name, pattern in ORIGINALS.items():
        src = find_original(pattern)
        if src is None:
            print(f"❌ Sin backup original para '{name}'")
            print(f"   Buscaba: backups_process/{pattern}")
            return 1
        found[name] = src
        print(f"✅ Original encontrado: {src.name}")

    pla_src = found["PLA Default @Kobra 2 Neo"]
    pla_data = json.loads(pla_src.read_text())

    # --- Construir el Wood derivado del PLA real ---
    wood = json.loads(json.dumps(pla_data))  # copia profunda
    wood["name"] = "PLA Wood Default @Kobra 2 Neo"
    for k in ("print_settings_id", "filament_settings_id"):
        if k in wood:
            wood[k] = ["PLA Wood Default @Kobra 2 Neo"] \
                if isinstance(wood[k], list) else "PLA Wood Default @Kobra 2 Neo"

    print("\nOverrides del wood sobre tu PLA real:")
    for k, v in WOOD_OVERRIDES.items():
        antes = wood.get(k, "(heredado)")
        wood[k] = v
        print(f"   {k:32s} {str(antes):>14s}  →  {v[0]}")

    print("\nSe CONSERVAN del original (el script generador los borraba):")
    kept = [k for k in pla_data if k.startswith(("support_", "seam_", "scarf_", "raft_"))]
    print(f"   {len(kept)} parámetros de soporte / costura / raft")
    print(f"   sparse_infill_density: {pla_data.get('sparse_infill_density')}"
          f"   (sin el '%%' duplicado)")

    if dry:
        print("\n🔍 DRY-RUN — no se escribió nada.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    quarantine = Path(__file__).parent / "_procesos_generados" / stamp
    quarantine.mkdir(parents=True, exist_ok=True)

    print()
    for name, src in found.items():
        dest = ORCA / f"{name}.json"
        if dest.exists():
            shutil.copy2(dest, quarantine / dest.name)
        shutil.copy2(src, dest)
        print(f"   ♻️  Restaurado: {name}.json")

    wood_dest = ORCA / "PLA Wood Default @Kobra 2 Neo.json"
    if wood_dest.exists():
        shutil.copy2(wood_dest, quarantine / wood_dest.name)
    wood_dest.write_text(json.dumps(wood, indent=2, ensure_ascii=False))
    print(f"   🪵 Creado: PLA Wood Default @Kobra 2 Neo.json (derivado del PLA)")

    print(f"\n📦 Versiones generadas guardadas en: {quarantine}")
    print("\n⚠️  NO vuelvas a correr generate_processes.py hasta extender su")
    print("   builder: borra soportes y scarf seam, y duplica el '%'.")
    print("\nSiguiente paso: Cmd+Q en OrcaSlicer y reabrir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
