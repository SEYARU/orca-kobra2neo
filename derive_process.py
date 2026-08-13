#!/usr/bin/env python3
"""
derive_process.py
==============================================================================
Crea un process preset NUEVO copiando uno existente del disco y aplicando
solo los overrides declarados. NO construye JSON desde cero.

POR QUE ASI Y NO CON UN GENERADOR
    generate_processes.py esta vetado: su builder conoce ~15 de 60+ campos
    y al reconstruir borra soportes, scarf seam y raft_first_layer_density.
    Destruyo 23 parametros el 2026-07-31.

    Aqui el JSON base se copia literal. Todo campo que no este en OVERRIDES
    sobrevive por arquitectura, no por disciplina. Es el mismo patron que
    uso restore_processes.py para derivar el Wood.

USO
    python3 derive_process.py --dry-run
    python3 derive_process.py
==============================================================================
"""
import json, shutil, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path.cwd()))
from orca_paths import account_dir

BACKUP_DIR = Path(__file__).parent / "backups_process"

ORIGEN  = "PLA Default @Kobra 2 Neo"
DESTINO = "PETG Default @Kobra 2 Neo"

# Valores STRING: OrcaSlicer serializa el JSON de proceso en texto.
# Un int en vez de "30" manda el preset a "Unsupported" sin avisar.
OVERRIDES = {
    # --- Velocidades: PETG funde mas lento que PLA y rezuma mucho mas ---
    "outer_wall_speed":            "30",
    "inner_wall_speed":            "45",
    "sparse_infill_speed":         "60",
    "internal_solid_infill_speed": "60",
    "top_surface_speed":           "30",
    "initial_layer_speed":         "20",
    "travel_speed":                "150",

    # --- Aceleraciones reducidas: el ooze del PETG empeora con tirones ---
    "default_acceleration":        "1500",
    "outer_wall_acceleration":     "800",

    # --- Primera capa mas alta: mejor adherencia, menos riesgo de arrancar
    #     el recubrimiento de la placa al despegar ---
    "initial_layer_print_height":  "0.25",

    # --- Skirt: 2 vueltas lentas. El PETG necesita purga real tras el
    #     calentamiento; el Bowden de 45cm rezuma todo ese rato ---
    "skirt_loops":                 "2",
    "skirt_distance":              "3",
    "skirt_speed":                 "25",
    "skirt_height":                "1",
    "skirt_type":                  "combined",
    "min_skirt_length":            "0",
    "draft_shield":                "disabled",
    "single_loop_draft_shield":    "0",

    # --- Brim fuera: el PETG se adhiere DEMASIADO al PEI texturizado.
    #     Se activa por objeto si una pieza concreta lo pide ---
    "brim_type":                   "no_brim",
    "brim_object_gap":             "0.2",

    # --- Elephant foot mayor: el PETG se aplasta mas en la primera capa ---
    "elefant_foot_compensation":   "0.2",
}


def main():
    dry = "--dry-run" in sys.argv
    d = account_dir() / "process"
    print(f"Cuenta detectada: {account_dir().name}\n")

    src = d / f"{ORIGEN}.json"
    dst = d / f"{DESTINO}.json"

    if not src.is_file():
        sys.exit(f"ERROR: no existe el origen {ORIGEN}.json")

    data = json.loads(src.read_text(encoding="utf-8"))
    n_orig = len(data)

    print(f"Origen : {ORIGEN}  ({n_orig} campos)")
    print(f"Destino: {DESTINO}{'  (YA EXISTE - se sobrescribe)' if dst.exists() else '  (nuevo)'}\n")

    data["name"] = DESTINO
    for k in ("print_settings_id",):
        if k in data:
            data[k] = DESTINO

    print(f"{'campo':<30}{'PLA':>14}  ->  PETG")
    print("-" * 62)
    for k, v in OVERRIDES.items():
        antes = data.get(k, "<heredado>")
        if isinstance(antes, list) and antes:
            antes = antes[0]
        print(f"{k:<30}{str(antes):>14}  ->  {v}")
        data[k] = v

    preservados = [k for k in data if k.startswith(("support_", "seam_", "scarf_", "raft_"))]
    print(f"\nPreservados del origen: {len(preservados)} campos de soporte/costura/raft")
    print(f"Total de campos: {n_orig} -> {len(data)}")

    if dry:
        print("\nDRY-RUN: no se escribio nada.")
        return

    if dst.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(dst, BACKUP_DIR / f"{DESTINO}_{stamp}.json")
        print(f"\nBackup: backups_process/{DESTINO}_{stamp}.json")

    assert len(data) >= n_orig, "ABORTADO: se perdieron campos"
    dst.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\nCreado: {DESTINO}.json")
    print("\nCmd+Q COMPLETO en OrcaSlicer y reabrir.")


if __name__ == "__main__":
    main()
