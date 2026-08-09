#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
CLEANUP.PY — Limpieza segura del ecosistema de perfiles OrcaSlicer
--------------------------------------------------------------------------------
Borra basura acumulada SIN tocar nada importante. Filosofía:
  1. ESCANEA y muestra TODO lo que encontró, agrupado por categoría
  2. Te pide confirmación POR CATEGORÍA (no un "sí" global ciego)
  3. Mueve a una papelera con fecha en vez de borrar de verdad (reversible)

NUNCA borra:
  - Tus YAML (la fuente de verdad)
  - Los scripts generadores
  - Los presets ACTIVOS en la carpeta de cuenta (UUID)
  - Perfiles de sistema de OrcaSlicer

Uso:
    python3 cleanup.py            # modo interactivo (recomendado)
    python3 cleanup.py --dry-run  # solo muestra, no toca nada
    python3 cleanup.py --hard     # borra de verdad en vez de mover a papelera
================================================================================
"""
import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from orca_paths import ORCA_ROOT as ORCA, preset_dir

HOME = Path.home()
PROJECT = Path(__file__).parent.absolute()
TRASH = PROJECT / f"_papelera_limpieza_{datetime.now():%Y%m%d_%H%M%S}"

# Presets que YA NO se usan (de la era de 5 presets, antes de consolidar a 2).
# Si alguno existe en la carpeta de cuenta, es basura obsoleta.
OBSOLETOS = [
    "PLA+ Print @Kobra 2 Neo",
    "PLA Grey Print @Kobra 2 Neo",
    "PLA Grey Preliminary @Kobra 2 Neo",
    "PLA+ Black Calibrated @Kobra 2 Neo",
    "TPU 95A Print @Kobra 2 Neo",
    "PLA Flexi Print @Kobra 2 Neo",
    "PLA Supports Print @Kobra 2 Neo",
    "Elegoo PLA+ Black Calibrated @Kobra 2 Neo",
    "Elegoo PLA Grey Preliminary @Kobra 2 Neo",
    "Elegoo TPU 95A Black Preliminary @Kobra 2 Neo",
]


def find_account_dir(subfolder):
    """Delegado a orca_paths (única implementación del proyecto)."""
    return preset_dir(subfolder, required=False)


def scan():
    """Escanea y agrupa la basura por categoría. Devuelve dict categoria→[paths]."""
    hallazgos = {}

    # 1. Caché de Python en el proyecto
    pycache = list(PROJECT.glob("**/__pycache__"))
    if pycache:
        hallazgos["Caché de Python (__pycache__)"] = pycache

    # 2. Papeleras de limpiezas anteriores
    viejas_papeleras = list(PROJECT.glob("_papelera_limpieza_*"))
    if viejas_papeleras:
        hallazgos["Papeleras de limpiezas anteriores"] = viejas_papeleras

    # 3. Backups acumulados por los generadores
    for bdir in ["backups", "backups_process"]:
        bpath = PROJECT / bdir
        if bpath.exists():
            files = list(bpath.glob("*.json"))
            if files:
                hallazgos[f"Backups en {bdir}/ ({len(files)} archivos)"] = files

    # 4. Duplicados obsoletos en default/ (la carpeta que OrcaSlicer ignora)
    for sub in ["process", "filament"]:
        ddir = ORCA / "user/default" / sub
        if ddir.exists():
            dups = list(ddir.glob("*@Kobra 2 Neo*"))
            if dups:
                hallazgos[f"Duplicados ignorados en default/{sub}/"] = dups

    # 5. Presets obsoletos en la carpeta de cuenta (era de 5 presets)
    for sub in ["process", "filament"]:
        adir = find_account_dir(sub)
        if adir:
            obs = []
            for name in OBSOLETOS:
                for ext in [".json", ".info"]:
                    p = adir / f"{name}{ext}"
                    if p.exists():
                        obs.append(p)
            if obs:
                hallazgos[f"Presets obsoletos (5-presets era) en cuenta/{sub}/"] = obs

    # 6. Backups viejos de versiones de OrcaSlicer (user_backup-vX.X.X)
    vbackups = list(ORCA.glob("user_backup-v*"))
    if vbackups:
        hallazgos["Backups de versiones viejas de OrcaSlicer"] = vbackups

    return hallazgos


def human_size(paths):
    """Tamaño total legible de una lista de paths."""
    total = 0
    for p in paths:
        if p.is_dir():
            total += sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        elif p.exists():
            total += p.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            return f"{total:.0f}{unit}"
        total /= 1024
    return f"{total:.0f}TB"


def main():
    ap = argparse.ArgumentParser(description="Limpieza segura de perfiles OrcaSlicer")
    ap.add_argument("--dry-run", action="store_true", help="Solo muestra, no toca nada")
    ap.add_argument("--hard", action="store_true", help="Borra de verdad (sin papelera)")
    args = ap.parse_args()

    print("=" * 70)
    print("🧹 Limpieza del ecosistema de perfiles OrcaSlicer")
    print("=" * 70)
    if args.dry_run:
        print("🔍 MODO DRY-RUN — no se toca ni un archivo\n")
    elif args.hard:
        print("⚠️  MODO HARD — borrado permanente, sin papelera\n")
    else:
        print(f"📦 Lo borrado se MUEVE a: {TRASH.name}/ (reversible)\n")

    hallazgos = scan()

    if not hallazgos:
        print("✨ Nada que limpiar. Tu setup ya está impecable.")
        return

    # Resumen
    print("Encontré esto:\n")
    for i, (cat, paths) in enumerate(hallazgos.items(), 1):
        print(f"  {i}. {cat}")
        print(f"     {len(paths)} elemento(s) · {human_size(paths)}")
        for p in paths[:4]:
            print(f"       - {p.name}")
        if len(paths) > 4:
            print(f"       ... y {len(paths)-4} más")
        print()

    if args.dry_run:
        print("🔍 Dry-run: no se borró nada. Quita --dry-run para limpiar.")
        return

    # Confirmar categoría por categoría
    if not args.hard:
        TRASH.mkdir(exist_ok=True)

    borrados = 0
    for cat, paths in hallazgos.items():
        resp = input(f"¿Limpiar '{cat}'? [y/N] ").strip().lower()
        if resp != "y":
            print("   ⏭️  Saltado\n")
            continue
        for p in paths:
            if not p.exists():
                continue
            if args.hard:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
            else:
                dest = TRASH / p.name
                # evitar colisiones de nombre
                k = 1
                while dest.exists():
                    dest = TRASH / f"{p.stem}_{k}{p.suffix}"
                    k += 1
                shutil.move(str(p), str(dest))
            borrados += 1
        print(f"   ✅ Limpio\n")

    print("=" * 70)
    if args.hard:
        print(f"🗑️  {borrados} elementos borrados permanentemente.")
    else:
        if borrados:
            print(f"📦 {borrados} elementos movidos a {TRASH.name}/")
            print("   Revisa que todo siga bien y borra esa carpeta cuando confíes.")
            print("   Para revertir: mueve los archivos de vuelta a su origen.")
        else:
            print("Nada se movió.")
            if TRASH.exists() and not any(TRASH.iterdir()):
                TRASH.rmdir()


if __name__ == "__main__":
    main()
