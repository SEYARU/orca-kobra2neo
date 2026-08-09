#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
GENERATE_PROFILES.PY
--------------------------------------------------------------------------------
Generador de perfiles de filamento de OrcaSlicer a partir de filaments.yaml.

USO:
    python generate_profiles.py                  # Genera todos los perfiles
    python generate_profiles.py --dry-run        # Solo muestra qué haría
    python generate_profiles.py --filament NOMBRE  # Solo uno específico

REQUISITOS:
    pip install pyyaml

FLUJO:
    1. Lee filaments.yaml
    2. Para cada filamento, construye el JSON con formato de OrcaSlicer
    3. Hace backup del archivo existente (si lo hay)
    4. Escribe el nuevo perfil en el directorio de OrcaSlicer
    5. Reporta lo que hizo

Después de ejecutar, reinicia OrcaSlicer para ver los cambios.
================================================================================
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from orca_paths import resolve_orca_dir as _resolve

try:
    import yaml
except ImportError:
    print("❌ Falta dependencia: pyyaml")
    print("   Instala con: pip install pyyaml")
    sys.exit(1)


# ============================================================================
# CONSTANTES Y CONFIGURACIÓN
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
YAML_CONFIG = SCRIPT_DIR / "filaments.yaml"
BACKUP_DIR = SCRIPT_DIR / "backups"

# Mapeo de tipo de filamento simple → tipo OrcaSlicer
FILAMENT_TYPE_MAP = {
    "PLA": "PLA",
    "PLA+": "PLA",       # OrcaSlicer no distingue, ambos son PLA internamente
    "TPU": "TPU",
    "PETG": "PETG",
    "ABS": "ABS",
    "ASA": "ASA",
}

# Densidad típica por material (g/cm³) - usado para cálculo de costo
DENSITY_MAP = {
    "PLA": 1.24,
    "TPU": 1.21,
    "PETG": 1.27,
    "ABS": 1.04,
    "ASA": 1.07,
}


# ============================================================================
# FUNCIONES DE CARGA Y VALIDACIÓN
# ============================================================================

def load_config():
    """Carga y valida el archivo filaments.yaml."""
    if not YAML_CONFIG.exists():
        print(f"❌ No se encontró el archivo: {YAML_CONFIG}")
        sys.exit(1)

    with open(YAML_CONFIG, "r", encoding="utf-8") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"❌ Error parseando YAML: {e}")
            sys.exit(1)

    # Validaciones básicas
    if "printer" not in config:
        print("❌ El YAML debe tener una sección 'printer'")
        sys.exit(1)

    if "filaments" not in config or not config["filaments"]:
        print("❌ El YAML debe tener al menos un filamento en 'filaments'")
        sys.exit(1)

    return config


def expand_path(path_str):
    """Expande ~ y variables de entorno en una ruta."""
    return Path(os.path.expandvars(os.path.expanduser(path_str)))


def resolve_orca_dir(path_str, subfolder):
    """Delegado a orca_paths (única implementación del proyecto)."""
    return _resolve(path_str, subfolder)


def validate_filament(filament, index):
    """Valida que un filamento tenga los campos mínimos requeridos."""
    required = ["name", "type", "settings"]
    for field in required:
        if field not in filament:
            print(f"❌ Filamento #{index + 1}: falta el campo '{field}'")
            return False

    if filament["type"] not in FILAMENT_TYPE_MAP:
        print(f"⚠️  Filamento '{filament['name']}': tipo '{filament['type']}' "
              f"no reconocido. Tipos soportados: {list(FILAMENT_TYPE_MAP.keys())}")
        return False

    return True


# ============================================================================
# GENERACIÓN DEL JSON DE ORCASLICER
# ============================================================================

def build_orca_profile(filament, orca_version, compatible_printer="", inherits_base="Anycubic Generic PLA"):
    """
    Construye el dict del perfil de filamento en formato OrcaSlicer
    usando el MODELO DE HERENCIA (inherits).

    En vez de generar los 122 campos standalone (que OrcaSlicer marca como
    Unsupported), heredamos de un perfil base del sistema y solo declaramos
    los campos que cambian. OrcaSlicer rellena el resto desde el base,
    incluyendo la compatibilidad de impresora.

    inherits_base: nombre del perfil de sistema del que heredar.
                   Por tipo: PLA/TPU/PETG → "Anycubic Generic PLA" funciona
                   como base universal, pero idealmente cada tipo hereda
                   de su propio base.
    """
    s = filament["settings"]
    filament_type = FILAMENT_TYPE_MAP[filament["type"]]

    # Perfil MÍNIMO con herencia. Solo los campos que sobreescribimos.
    # OrcaSlicer hereda todo lo demás (incluyendo compatible_printers) del base.
    profile = {
        # Metadata e identidad
        "type": "filament",
        "name": filament["name"],
        "from": "User",
        "is_custom_defined": "1",
        "version": f"{orca_version}.0",
        "inherits": inherits_base,   # ← CLAVE: hereda del perfil de sistema

        # Tipo y vendor (por si difieren del base)
        "filament_type": [filament_type],
        "filament_vendor": [filament.get("vendor", "Generic")],

        # Temperaturas del nozzle
        "nozzle_temperature": [str(s["nozzle_temp"])],
        "nozzle_temperature_initial_layer": [str(s["first_layer_temp"])],

        # Temperaturas de la cama
        "hot_plate_temp": [str(s["bed_temp"])],
        "hot_plate_temp_initial_layer": [str(s["first_layer_bed"])],
        "textured_plate_temp": [str(s["bed_temp"])],
        "textured_plate_temp_initial_layer": [str(s["first_layer_bed"])],

        # Flow
        "filament_flow_ratio": [str(s["flow_ratio"])],
        "filament_max_volumetric_speed": [str(s["max_volumetric_speed"])],

        # Retracción
        "filament_retraction_length": [str(s["retraction"])],
        "filament_retraction_speed": [str(s["retraction_speed"])],
        "filament_z_hop": [str(s["z_hop"])],
        "filament_z_hop_types": [s.get("z_hop_type", "Slope Lift")],

        # Cooling
        "fan_max_speed": [str(s["fan_speed"])],
        "overhang_fan_speed": [str(s["fan_speed"])],
        "close_fan_the_first_x_layers": [str(s["disable_fan_first_layers"])],
        "slow_down_layer_time": [str(s["min_layer_time"])],
        "slow_down_min_speed": [str(s["min_print_speed"])],

        # Pressure Advance / Linear Advance
        "enable_pressure_advance": ["1" if s["pressure_advance"] > 0 else "0"],
        "pressure_advance": [str(s["pressure_advance"])],

        # Color (cosmético)
        "default_filament_colour": [filament.get("color", "")],
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

    return profile


def save_profile(profile, output_path, dry_run=False):
    """
    Guarda el perfil JSON en la ubicación destino.
    Hace backup del archivo existente si lo hay.
    """
    if dry_run:
        print(f"   [DRY-RUN] Escribiría a: {output_path}")
        return

    # Backup si ya existe
    if output_path.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{output_path.stem}_{timestamp}.json"
        backup_path = BACKUP_DIR / backup_name
        backup_path.write_text(output_path.read_text(encoding="utf-8"),
                               encoding="utf-8")
        print(f"   📦 Backup: {backup_path.name}")

    # Escribir el nuevo perfil
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4, ensure_ascii=False)


# ============================================================================
# FLUJO PRINCIPAL
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generador de perfiles de filamento para OrcaSlicer"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra qué haría, sin escribir archivos"
    )
    parser.add_argument(
        "--filament",
        type=str,
        help="Genera solo el filamento con este nombre (o substring)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("🖨️  Generador de perfiles OrcaSlicer")
    print("=" * 70)

    # Cargar config
    config = load_config()
    printer = config["printer"]
    filaments = config["filaments"]

    output_dir = resolve_orca_dir(printer["profile_path"], "filament")
    orca_version = printer.get("orca_version", "2.3.2")
    compatible_printer = printer.get("compatible_printer", "")
    inherit_base_map = printer.get("inherit_base", {})

    print(f"📁 Directorio destino: {output_dir}")
    if "default" in str(output_dir).split("/user/")[-1].split("/")[0]:
        print("   ⚠️  Escribiendo en default/ (sin cuenta detectada).")
        print("      Si OrcaSlicer no ve los cambios, inicia sesión y reintenta.")
    else:
        print("   ✅ Carpeta de cuenta detectada (donde OrcaSlicer realmente lee)")
    print(f"🏷️  Impresora: {printer['name']}")
    if inherit_base_map:
        print(f"🧬 Modelo de herencia activo (bases: {list(inherit_base_map.values())})")
    else:
        print(f"⚠️  SIN bases de herencia → perfiles pueden salir como Unsupported")
    print(f"📦 Filamentos a procesar: {len(filaments)}")
    if args.dry_run:
        print("🔍 MODO DRY-RUN (no se escriben archivos)")
    print()

    # Validar que el directorio existe (si no es dry-run)
    if not args.dry_run and not output_dir.exists():
        print(f"⚠️  El directorio destino no existe: {output_dir}")
        response = input("   ¿Crearlo? (y/N): ").strip().lower()
        if response != "y":
            print("❌ Cancelado por el usuario")
            sys.exit(1)
        output_dir.mkdir(parents=True, exist_ok=True)

    # Procesar cada filamento
    success_count = 0
    skip_count = 0
    error_count = 0

    for index, filament in enumerate(filaments):
        name = filament.get("name", f"<sin nombre #{index + 1}>")

        # Filtrar por nombre si se especificó
        if args.filament and args.filament.lower() not in name.lower():
            continue

        print(f"▶ {name}")

        # Validar
        if not validate_filament(filament, index):
            error_count += 1
            print()
            continue

        # Marcar visualmente si está calibrado
        if filament.get("calibrated"):
            print(f"   ✅ Estado: CALIBRADO")
        else:
            print(f"   ⚠️  Estado: PRELIMINAR (pendiente calibración)")

        # Construir perfil
        # Resolver el perfil base del que hereda este filamento (por tipo)
        ftype = filament["type"]
        inherits_base = inherit_base_map.get(ftype, "Anycubic Generic PLA")

        try:
            profile = build_orca_profile(filament, orca_version,
                                         compatible_printer, inherits_base)
            print(f"   🧬 Hereda de: {inherits_base}")
        except KeyError as e:
            print(f"   ❌ Falta parámetro en settings: {e}")
            error_count += 1
            print()
            continue

        # Guardar
        # OrcaSlicer usa el name como filename (con espacios y todo)
        output_path = output_dir / f"{name}.json"

        try:
            save_profile(profile, output_path, dry_run=args.dry_run)
            print(f"   💾 {'Simulado' if args.dry_run else 'Generado'}: "
                  f"{output_path.name}")
            success_count += 1
        except (IOError, OSError) as e:
            print(f"   ❌ Error al escribir: {e}")
            error_count += 1

        print()

    # Resumen
    print("=" * 70)
    print(f"📊 RESUMEN")
    print("=" * 70)
    print(f"   ✅ Generados:  {success_count}")
    if skip_count > 0:
        print(f"   ⏭️  Saltados:   {skip_count}")
    if error_count > 0:
        print(f"   ❌ Errores:    {error_count}")
    print()

    if success_count > 0 and not args.dry_run:
        print("🎯 PRÓXIMOS PASOS:")
        print("   1. Cierra OrcaSlicer si está abierto")
        print("   2. Vuelve a abrirlo")
        print("   3. Filament Settings → verás los nuevos perfiles")
        print()

    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
