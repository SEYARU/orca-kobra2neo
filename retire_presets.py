#!/usr/bin/env python3
"""
retire_presets.py
------------------------------------------------------------------------------
Retira presets viejos de OrcaSlicer de forma SEGURA y REVERSIBLE.

Deja únicamente los 3 perfiles generados por el sistema declarativo:
    Elegoo PLA @Kobra 2 Neo
    Elegoo PLA Wood @Kobra 2 Neo
    Elegoo TPU 95A Black @Kobra 2 Neo

POR QUÉ EXISTE ESTE SCRIPT
    Borrar archivos con OrcaSlicer ABIERTO no funciona: al cerrarse, el
    slicer vuelca sus presets en memoria al disco y los recrea. Por eso
    "volvieron" la vez anterior. Este script verifica que esté cerrado
    antes de tocar nada.

QUÉ HACE
    - Aborta si OrcaSlicer está corriendo
    - Mueve (no borra) cada preset y su .info acompañante a una cuarentena
      FUERA del árbol de OrcaSlicer
    - Imprime el comando exacto para revertir

Uso:
    python3 retire_presets.py --dry-run
    python3 retire_presets.py
    python3 retire_presets.py --restore
"""

import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime

from orca_paths import ORCA_ROOT, account_dir

# Presets que SE QUEDAN. Todo lo demás en esas carpetas se retira.
KEEP = {
    "filament": {
        "Elegoo PLA @Kobra 2 Neo",
        "Elegoo PLA Wood @Kobra 2 Neo",
        "Elegoo TPU 95A Black @Kobra 2 Neo",
    },
    "process": {
        "PLA Default @Kobra 2 Neo",
        "PLA Wood Default @Kobra 2 Neo",
        "TPU 95A Default @Kobra 2 Neo",
    },
}

QUARANTINE = Path(__file__).parent / "_retirados"


def orcaslicer_running():
    """
    Detecta el proceso de la app.

    Usa 'pgrep -x' (coincidencia EXACTA del nombre de proceso) y no '-f'.
    Con '-f' se busca en la línea de comandos completa, así que cualquier
    shell que tenga la ruta de OrcaSlicer en su comando —por ejemplo tras
    un ORCA="...OrcaSlicer..."— daría falso positivo.
    """
    try:
        out = subprocess.run(["pgrep", "-x", "OrcaSlicer"],
                             capture_output=True, text=True)
        return out.returncode == 0 and bool(out.stdout.strip())
    except Exception:
        return None  # no se pudo determinar


def scan():
    """Devuelve [(ruta, carpeta_logica)] de todo lo que hay que retirar."""
    hits = []
    for scope in ("filament", "process"):
        for parent in (account_dir(), ORCA_ROOT / "user" / "default"):
            d = parent / scope
            if not d.exists():
                continue
            for f in sorted(d.iterdir()):
                if f.name.startswith("."):        # .DS_Store y similares
                    continue
                if f.suffix not in (".json", ".info"):
                    continue
                if f.stem in KEEP[scope]:
                    continue
                hits.append((f, f"{parent.name}/{scope}"))
    return hits


def restore():
    if not QUARANTINE.exists():
        print("❌ No hay cuarentena que restaurar.")
        return 1
    n = 0
    for batch in sorted(QUARANTINE.iterdir()):
        if not batch.is_dir():
            continue
        for scope_dir in batch.iterdir():
            if not scope_dir.is_dir():
                continue
            parent_name, scope = scope_dir.name.split("__")
            dest = ORCA_ROOT / "user" / parent_name / scope
            dest.mkdir(parents=True, exist_ok=True)
            for f in scope_dir.iterdir():
                shutil.move(str(f), str(dest / f.name))
                print(f"   ↩️  {f.name} → {parent_name}/{scope}")
                n += 1
    print(f"\n✅ Restaurados {n} archivo(s). Reinicia OrcaSlicer.")
    return 0


def main():
    if "--restore" in sys.argv:
        return restore()

    dry = "--dry-run" in sys.argv

    print("=" * 70)
    print("🧹 Retiro de presets viejos de OrcaSlicer")
    print("=" * 70)

    running = orcaslicer_running()
    if running:
        print("❌ OrcaSlicer está ABIERTO.")
        print("   Ciérralo con Cmd+Q (completo, no solo la ventana) y reintenta.")
        print("   Si lo haces con el slicer abierto, al cerrarse vuelve a")
        print("   escribir sus presets en memoria y los archivos reaparecen.")
        return 1
    if running is None:
        print("⚠️  No pude verificar si OrcaSlicer está corriendo. Asegúrate de")
        print("   haberlo cerrado con Cmd+Q antes de continuar.")

    hits = scan()
    if not hits:
        print("✅ Nada que retirar. Solo están los 3 + 3 esperados.")
        return 0

    print(f"\nSe van a retirar {len(hits)} archivo(s):\n")
    for f, loc in hits:
        print(f"   - [{loc}] {f.name}")

    print("\nSe QUEDAN:")
    for scope in ("filament", "process"):
        for name in sorted(KEEP[scope]):
            print(f"   ✓ [{scope}] {name}")

    if dry:
        print("\n🔍 DRY-RUN — no se movió nada.")
        return 0

    resp = input("\n¿Continuar? [y/N] ").strip().lower()
    if resp != "y":
        print("Cancelado. Nada se movió.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch = QUARANTINE / stamp
    for f, loc in hits:
        parent_name, scope = loc.split("/")
        dest = batch / f"{parent_name}__{scope}"
        dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dest / f.name))
        print(f"   📦 {f.name}")

    print(f"\n✅ {len(hits)} archivo(s) movidos a: {batch}")
    print("\nPara revertir:")
    print("   python3 retire_presets.py --restore")
    print("\nSiguiente paso: abre OrcaSlicer y verifica que estén los 3 + 3.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
