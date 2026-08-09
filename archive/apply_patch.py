#!/usr/bin/env python3
"""
apply_patch.py
------------------------------------------------------------------------------
Parcha generate_profiles.py para que propague 'compatible_prints_condition'
desde el YAML al JSON de OrcaSlicer.

Sin este parche, build_orca_profile() construye el dict campo por campo y
descarta en silencio cualquier clave que no conozca. Resultado: el blindaje
del PLA Wood no existe y puedes rebanarlo con el proceso de PLA a 90 mm/s
sin que nada te avise.

Propiedades:
  - Hace backup con timestamp antes de tocar nada
  - Es idempotente: si ya está parcheado, no hace nada
  - Si no encuentra el anclaje, aborta sin modificar el archivo

Uso:
    python3 apply_patch.py
    python3 apply_patch.py --dry-run
"""

import sys
import shutil
from datetime import datetime
from pathlib import Path

TARGET = Path(__file__).parent / "generate_profiles.py"

# Anclaje: las últimas líneas del dict + el return de build_orca_profile()
ANCHOR = '''        "default_filament_colour": [filament.get("color", "")],
    }

    return profile'''

REPLACEMENT = '''        "default_filament_colour": [filament.get("color", "")],
    }

    # ---- Restricción opcional de procesos compatibles ----
    # Blindaje del PLA Wood: impide seleccionarlo con un proceso que no
    # tenga "Wood" en el nombre.
    # OJO: string PLANO, no lista. El resto de campos van como lista de un
    # elemento porque OrcaSlicer los trata como vectores por extrusor, pero
    # los campos de compatibilidad son strings. Envolverlo en lista hace
    # que OrcaSlicer lo ignore.
    if "compatible_prints_condition" in s:
        profile["compatible_prints_condition"] = s["compatible_prints_condition"]

    return profile'''

MARKER = 'profile["compatible_prints_condition"]'


def main():
    dry = "--dry-run" in sys.argv

    if not TARGET.exists():
        print(f"❌ No encuentro {TARGET.name} en esta carpeta.")
        print("   Corre este script desde filament-profile-manager/")
        return 1

    src = TARGET.read_text()

    if MARKER in src:
        print("✅ Ya está parcheado. No hay nada que hacer.")
        return 0

    if ANCHOR not in src:
        print("❌ No encuentro el anclaje esperado en build_orca_profile().")
        print("   El script cambió desde que se escribió este parche.")
        print("   Aplícalo a mano: antes del 'return profile' final agrega:")
        print()
        print('       if "compatible_prints_condition" in s:')
        print('           profile["compatible_prints_condition"] = \\')
        print('               s["compatible_prints_condition"]')
        return 1

    if src.count(ANCHOR) > 1:
        print("❌ El anclaje aparece más de una vez. Aborto por seguridad.")
        return 1

    if dry:
        print("🔍 DRY-RUN — anclaje encontrado, el parche aplicaría limpio.")
        print("   Corre sin --dry-run para escribirlo.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = TARGET.with_name(f"{TARGET.stem}_{stamp}.py.bak")
    shutil.copy2(TARGET, backup)
    print(f"📦 Backup: {backup.name}")

    TARGET.write_text(src.replace(ANCHOR, REPLACEMENT))
    print(f"✅ Parcheado: {TARGET.name}")
    print()
    print("Siguiente paso:")
    print("   python3 generate_profiles.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
