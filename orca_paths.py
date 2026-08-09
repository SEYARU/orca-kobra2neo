#!/usr/bin/env python3
"""
orca_paths.py
==============================================================================
Única fuente de verdad para localizar dónde OrcaSlicer lee sus presets.

POR QUÉ EXISTE
    El proyecto tenía TRES implementaciones distintas de la misma lógica
    (generate_profiles.resolve_orca_dir, cleanup.find_account_dir,
    generate_processes.resolve_orca_dir) y TRES scripts con el UUID de la
    cuenta escrito a mano (export_processes, restore_processes,
    retire_presets).

    Un UUID hardcodeado no falla ruidosamente: falla en silencio. Si
    cambias de cuenta o OrcaSlicer regenera la carpeta, retire_presets.py
    escanea una ruta inexistente, encuentra cero archivos y reporta
    "✅ Nada que retirar" — un visto bueno falso.

CÓMO FUNCIONA
    OrcaSlicer guarda en user/default/<tipo>/ cuando no hay sesión, y en
    user/<UUID>/<tipo>/ cuando sí la hay. La carpeta de cuenta GANA: si
    existe y escribes en default/, el preset nunca aparece en el dropdown.

    account_dir() detecta la carpeta UUID activa sin hardcodear nada.
==============================================================================
"""

import os
import sys
from pathlib import Path

ORCA_ROOT = Path.home() / "Library/Application Support/OrcaSlicer"
ORCA_USER = ORCA_ROOT / "user"

KINDS = ("filament", "process", "machine")


def expand_path(path_str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path_str))))


def is_uuid(name: str) -> bool:
    return len(name) == 36 and name.count("-") == 4


def account_dir(required: bool = True):
    """
    Carpeta de cuenta activa (user/<UUID>/), o None si no hay.

    Si hay varias, gana la que más presets tiene — mismo criterio que usaba
    generate_profiles.py, por compatibilidad.
    """
    if not ORCA_USER.is_dir():
        if required:
            sys.exit(f"❌ No existe: {ORCA_USER}\n   ¿OrcaSlicer instalado en otra ruta?")
        return None

    scored = []
    for child in ORCA_USER.iterdir():
        if not child.is_dir() or child.name == "default" or not is_uuid(child.name):
            continue
        n = sum(len(list((child / k).glob("*.json")))
                for k in KINDS if (child / k).is_dir())
        if n:
            scored.append((n, child))

    if not scored:
        if required:
            sys.exit(
                f"❌ Sin carpeta de cuenta con presets en:\n   {ORCA_USER}\n"
                "   Inicia sesión en OrcaSlicer y reintenta."
            )
        return None

    scored.sort(key=lambda t: (t[0], t[1].name), reverse=True)
    return scored[0][1]


def preset_dir(kind: str, required: bool = True):
    """Carpeta de un tipo de preset dentro de la cuenta activa."""
    if kind not in KINDS:
        raise ValueError(f"kind debe ser uno de {KINDS}, no {kind!r}")
    acc = account_dir(required=required)
    if acc is None:
        return None
    d = acc / kind
    if not d.is_dir():
        if required:
            sys.exit(f"❌ No existe: {d}")
        return None
    return d


def resolve_orca_dir(path_str, subfolder):
    """
    COMPATIBILIDAD: misma firma y semántica que la función original de
    generate_profiles.py. Resuelve la carpeta de cuenta a partir de un
    profile_path del YAML; si no la encuentra, devuelve el path configurado
    tal cual (comportamiento histórico — no romperlo).
    """
    configured = expand_path(path_str)

    user_dir = next(
        (p for p in [configured] + list(configured.parents) if p.name == "user"),
        None,
    )
    if user_dir is None or not user_dir.exists():
        return configured

    candidates = []
    for child in user_dir.iterdir():
        if not child.is_dir() or child.name == "default" or not is_uuid(child.name):
            continue
        sub = child / subfolder
        if sub.exists() and any(sub.glob("*.json")):
            candidates.append((len(list(sub.glob("*.json"))), child.name, sub))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2]
    return configured


def banner():
    """Línea de confirmación estándar. Todos los scripts imprimen la misma."""
    acc = account_dir()
    print(f"✅ Cuenta detectada: {acc.name}")
    return acc


if __name__ == "__main__":
    acc = banner()
    for k in KINDS:
        d = acc / k
        n = len(list(d.glob("*.json"))) if d.is_dir() else 0
        print(f"   {k:<10} {n} preset(s)")
