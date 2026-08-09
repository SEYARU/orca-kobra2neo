#!/usr/bin/env python3
"""
export_processes.py
------------------------------------------------------------------------------
Exporta los process presets ACTUALES a documentación versionable.

EL PROBLEMA QUE RESUELVE
    generate_processes.py está vetado (su builder solo conoce 15 de los 60+
    campos y borra soportes y scarf seam al regenerar). Eso deja los procesos
    sin versionar: si se pierden, no hay forma de reconstruirlos.

    Este script cierra ese hueco en la dirección segura. No genera nada:
    LEE lo que OrcaSlicer tiene y escribe una copia fiel más un resumen
    legible. Es de una sola vía, así que no puede romper nada.

SALIDA
    processes_snapshot/<fecha>/*.json   copia exacta, restaurable
    PROCESOS.md                         tabla comparativa de los 3 presets

CUÁNDO CORRERLO
    Después de ajustar cualquier proceso en la UI de OrcaSlicer.
    Súbelo a git y tienes historial de cambios igual que con los filamentos.

Uso:
    python3 export_processes.py
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

ORCA = Path.home() / (
    "Library/Application Support/OrcaSlicer/user/"
    "ba9291fb-5260-4dc6-8ff3-0c3be79554dc/process"
)

PRESETS = [
    "PLA Default @Kobra 2 Neo",
    "PLA Wood Default @Kobra 2 Neo",
    "TPU 95A Default @Kobra 2 Neo",
]

# Campos destacados en la tabla comparativa, en orden de interés
HIGHLIGHT = [
    ("layer_height", "Altura de capa"),
    ("initial_layer_print_height", "Altura 1ª capa"),
    ("wall_loops", "Paredes"),
    ("top_shell_layers", "Capas superiores"),
    ("bottom_shell_layers", "Capas inferiores"),
    ("sparse_infill_density", "Relleno"),
    ("sparse_infill_pattern", "Patrón relleno"),
    ("brim_width", "Brim"),
    ("outer_wall_speed", "Pared exterior"),
    ("inner_wall_speed", "Pared interior"),
    ("sparse_infill_speed", "Relleno (vel.)"),
    ("top_surface_speed", "Superficie sup."),
    ("initial_layer_speed", "1ª capa (vel.)"),
    ("travel_speed", "Viaje"),
    ("default_acceleration", "Aceleración"),
    ("outer_wall_acceleration", "Acel. pared ext."),
    ("seam_position", "Costura"),
    ("support_type", "Tipo soporte"),
    ("support_top_z_distance", "Soporte Z sup."),
    ("support_object_xy_distance", "Soporte XY"),
]


def flat(v):
    """Los valores vienen como lista de un elemento (vectores por extrusor)."""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def main():
    if not ORCA.exists():
        print(f"❌ No existe {ORCA}")
        return 1

    print("=" * 70)
    print("📤 Exportando process presets a documentación")
    print("=" * 70)

    data = {}
    for name in PRESETS:
        f = ORCA / f"{name}.json"
        if not f.exists():
            print(f"⚠️  Falta: {name}.json — se omite")
            continue
        data[name] = json.loads(f.read_text())
        print(f"✅ Leído: {name}.json ({len(data[name])} campos)")

    if not data:
        print("❌ No se encontró ningún preset.")
        return 1

    here = Path(__file__).parent

    # --- 1. Copia fiel, restaurable ---
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap = here / "processes_snapshot" / stamp
    snap.mkdir(parents=True, exist_ok=True)
    for name in data:
        shutil.copy2(ORCA / f"{name}.json", snap / f"{name}.json")
    print(f"\n📦 Copia exacta: processes_snapshot/{stamp}/")

    # --- 2. Resumen legible ---
    lines = [
        "# Process Presets — Anycubic Kobra 2 Neo",
        "",
        f"Exportado: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "> Generado por `export_processes.py`. **No editar a mano.**",
        "> Los procesos se ajustan en la UI de OrcaSlicer; después se",
        "> re-exporta este archivo. `generate_processes.py` está vetado:",
        "> su builder borra soportes y scarf seam al regenerar.",
        "",
        "## Comparativa",
        "",
    ]

    cols = list(data.keys())
    short = [c.replace(" @Kobra 2 Neo", "") for c in cols]
    lines.append("| Parámetro | " + " | ".join(short) + " |")
    lines.append("|---|" + "---|" * len(cols))

    for key, label in HIGHLIGHT:
        vals = [flat(data[c].get(key, "—")) for c in cols]
        if all(v == "—" for v in vals):
            continue
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    # --- 3. Diferencias respecto al PLA (el preset de referencia) ---
    base_name = cols[0]
    base = data[base_name]
    for other in cols[1:]:
        d = data[other]
        diffs = sorted(
            k for k in set(base) | set(d)
            if base.get(k) != d.get(k) and k not in ("name", "print_settings_id")
        )
        lines += [
            "",
            f"## {other.replace(' @Kobra 2 Neo','')} — diferencias vs "
            f"{base_name.replace(' @Kobra 2 Neo','')}",
            "",
        ]
        if not diffs:
            lines.append("_Idéntico._")
            continue
        lines.append("| Campo | PLA | Este |")
        lines.append("|---|---|---|")
        for k in diffs:
            lines.append(f"| `{k}` | {flat(base.get(k,'—'))} | {flat(d.get(k,'—'))} |")

    # --- 4. Inventario de campos ---
    lines += ["", "## Campos por preset", ""]
    for name, d in data.items():
        grupos = {}
        for k in d:
            g = k.split("_")[0]
            grupos[g] = grupos.get(g, 0) + 1
        top = sorted(grupos.items(), key=lambda x: -x[1])[:6]
        resumen = ", ".join(f"{g} ({n})" for g, n in top)
        lines.append(f"- **{name}** — {len(d)} campos · {resumen}")

    out = here / "PROCESOS.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"📄 Resumen: {out.name}")

    print("\nSúbelo a git y tendrás historial de los procesos, igual que")
    print("con los filamentos — pero sin el riesgo de regenerarlos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
