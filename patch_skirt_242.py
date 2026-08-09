#!/usr/bin/env python3
"""
patch_skirt_242.py
==============================================================================
Ajusta los parámetros de skirt en los process presets de OrcaSlicer 2.4.2,
con valores DIFERENCIADOS por material.

POR QUÉ NO USAR generate_processes.py
    Su builder conoce ~15 de 60+ campos y al reconstruir el JSON borra
    soportes, scarf seam y raft_first_layer_density. El 2026-07-31 destruyó
    23 parámetros calibrados.

    Este script hace read -> modify N claves -> write. Todo lo que no esté
    en PATCHES sobrevive por arquitectura, no por disciplina.

CAMBIOS 2.4.x (verificados contra el wiki oficial)
    No hubo renombres de campos. El overhaul de skirt de 2.4.0 fue del
    algoritmo de generación, no del esquema. Pero 2.4.x expone campos que
    un preset creado en 2.3.2 puede no tener:
        min_skirt_length         <- sospechoso principal de sobre-extrusión
        skirt_type               <- combined / perobject
        skirt_start_angle
        skirt_speed
        single_loop_draft_shield

USO
    python3 patch_skirt_242.py --dry-run
    python3 patch_skirt_242.py
    python3 patch_skirt_242.py --restore
==============================================================================
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

from orca_paths import account_dir

BACKUP_DIR = Path(__file__).parent / "backups_process"


# ===========================================================================
# LOS PARCHES — valores por perfil. Todo STRING: OrcaSlicer serializa el
# JSON de proceso en texto. Un int en vez de "1" manda el preset a
# "Unsupported" sin avisar.
# ===========================================================================

PATCHES = {

    # -----------------------------------------------------------------
    # PLA — el caso común. La Kobra 2 Neo ya purga en el start G-code,
    # así que el skirt solo confirma nivelado y estabiliza presión.
    # -----------------------------------------------------------------
    "PLA Default @Kobra 2 Neo": {
        "skirt_loops":             "1",
        "skirt_distance":          "2",
        "skirt_height":            "1",
        "skirt_type":              "combined",
        "skirt_speed":             "0",         # 0 = usa velocidad de 1ª capa
        "min_skirt_length":        "0",         # CRÍTICO: ya hay prime line
        "draft_shield":            "disabled",
        "single_loop_draft_shield": "0",
    },

    # -----------------------------------------------------------------
    # PLA WOOD — fibra, propenso a clog, max_volumetric_speed 8.
    # Aquí el skirt SÍ trabaja: purga la fibra reseca del nozzle antes
    # de tocar la pieza. Más vueltas y lento a propósito.
    # -----------------------------------------------------------------
    "PLA Wood Default @Kobra 2 Neo": {
        "skirt_loops":             "2",
        "skirt_distance":          "2",
        "skirt_height":            "1",
        "skirt_type":              "combined",
        "skirt_speed":             "20",        # lento: la fibra no perdona
        "min_skirt_length":        "0",
        "draft_shield":            "disabled",
        "single_loop_draft_shield": "0",
    },

    # -----------------------------------------------------------------
    # TPU 95A — Bowden de 45 cm. El material rezuma durante todo el
    # calentamiento y la primera capa sale irregular sin purga real.
    # Distancia mayor: el stringing del TPU alcanza la pieza a 2mm.
    # -----------------------------------------------------------------
    "TPU 95A Default @Kobra 2 Neo": {
        "skirt_loops":             "3",
        "skirt_distance":          "3",
        "skirt_height":            "1",
        "skirt_type":              "combined",
        "skirt_speed":             "15",        # TPU rápido = no adhiere
        "min_skirt_length":        "0",
        "draft_shield":            "disabled",
        "single_loop_draft_shield": "0",
    },
}


# ===========================================================================
def resolve_process_dir() -> Path:
    acc = account_dir()
    print(f"✅ Cuenta detectada: {acc.name}\n")
    return acc / "process"


def apply_patch(path: Path, patch: dict, dry_run: bool) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    n_before = len(data)

    changes = [
        (k, data.get(k, "⟨ausente⟩"), v)
        for k, v in patch.items()
        if data.get(k, "⟨ausente⟩") != v
    ]

    if not changes:
        print(f"   ✓ {path.stem} — sin cambios")
        return False

    print(f"   📝 {path.stem}")
    for k, old, new in changes:
        flag = "  🆕 campo nuevo de 2.4.x" if old == "⟨ausente⟩" else ""
        print(f"      {k:<26} {str(old):>12}  ->  {new}{flag}")

    if dry_run:
        return True

    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, BACKUP_DIR / f"{path.stem}_{stamp}.json")

    for k, _, new in changes:
        data[k] = new

    assert len(data) >= n_before, "❌ ABORTADO: se perdieron campos"
    path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    return True


def restore(process_dir: Path):
    if not BACKUP_DIR.is_dir():
        sys.exit("❌ No hay backups.")
    for target in PATCHES:
        backups = sorted(BACKUP_DIR.glob(f"{target}_*.json"))
        if not backups:
            print(f"   ⚠️  Sin backup para {target}")
            continue
        shutil.copy2(backups[-1], process_dir / f"{target}.json")
        print(f"   ↩️  {target}  <-  {backups[-1].name}")


def main():
    dry_run = "--dry-run" in sys.argv
    process_dir = resolve_process_dir()

    if "--restore" in sys.argv:
        print("↩️  RESTAURANDO\n")
        restore(process_dir)
        print("\nCmd+Q completo en OrcaSlicer.")
        return

    print("🔍 DRY-RUN — no se escribe nada\n" if dry_run else "🔧 APLICANDO\n")

    touched = sum(
        apply_patch(process_dir / f"{t}.json", p, dry_run)
        for t, p in PATCHES.items()
        if (process_dir / f"{t}.json").is_file()
        or print(f"   ⚠️  No existe: {t}.json")
    )

    print(f"\n{'Se modificarían' if dry_run else 'Modificados'}: {touched} preset(s)")
    if not dry_run and touched:
        print(f"Backups: {BACKUP_DIR}")
        print("\n⚠️  Cmd+Q COMPLETO en OrcaSlicer. Cerrar la ventana no basta.")


if __name__ == "__main__":
    main()
