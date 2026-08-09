#!/usr/bin/env python3
"""
resolve_inherited.py — READ-ONLY
Resuelve el valor EFECTIVO de un campo recorriendo la cadena de herencia.

TRAMPA QUE ESTE SCRIPT EVITA
    Nombres como 'fdm_process_common' existen bajo VARIOS fabricantes
    (Anycubic/, Custom/, ...) con valores DISTINTOS. Indexar solo por
    nombre de archivo te hace resolver contra el de otra marca y reportar
    un valor que no es el tuyo.

    Caso real: el fdm_process_common de Custom declara min_skirt_length=4;
    el de Anycubic no lo declara. Indexar plano reportaba 4 cuando el
    valor real era el default interno de OrcaSlicer (0).

    Solución: se prioriza el fabricante del perfil que se está resolviendo.

Uso:
    python3 resolve_inherited.py
    python3 resolve_inherited.py "Elegoo TPU 95A Calibrated @Kobra 2 Neo"
    python3 resolve_inherited.py "TPU 95A Default @Kobra 2 Neo" --process
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from orca_paths import ORCA_ROOT, preset_dir

SYSTEM = ORCA_ROOT / "system"

CAMPOS = {
    "filament": [
        "hot_plate_temp", "hot_plate_temp_initial_layer", "fan_max_speed",
        "slow_down_min_speed", "filament_flow_ratio", "nozzle_temperature",
        "filament_max_volumetric_speed", "filament_retraction_length",
    ],
    "process": [
        "skirt_loops", "skirt_distance", "skirt_height", "skirt_type",
        "skirt_speed", "min_skirt_length", "draft_shield",
        "single_loop_draft_shield", "brim_type", "brim_width",
        "layer_height", "sparse_infill_density",
    ],
}


def index_system(kind):
    """
    Devuelve (by_vendor, flat). by_vendor evita colisiones entre marcas.
    """
    by_vendor, flat = {}, {}
    if SYSTEM.is_dir():
        for f in SYSTEM.glob(f"*/{kind}/*.json"):
            by_vendor[(f.parts[-3], f.stem)] = f
            flat.setdefault(f.stem, f)
    return by_vendor, flat


def chain(start_path, by_vendor, flat, vendor, limit=12):
    """[(nombre, dict, fabricante)] desde el perfil hasta la raíz."""
    out, cur, name, seen = [], start_path, start_path.stem, set()
    for _ in range(limit):
        if cur is None or name in seen:
            break
        seen.add(name)
        try:
            data = json.loads(cur.read_text())
        except Exception as e:
            out.append((f"{name} <ilegible: {e}>", {}, "?"))
            break
        src_vendor = cur.parts[-3] if SYSTEM in cur.parents else "USUARIO"
        out.append((name, data, src_vendor))
        parent = data.get("inherits")
        if not parent:
            break
        name = parent
        nxt = by_vendor.get((vendor, parent)) if vendor else None
        if nxt is None:
            nxt = flat.get(parent)
            if nxt is not None and vendor:
                print(f"   [aviso] '{parent}' no existe bajo {vendor}/, "
                      f"usando el de {nxt.parts[-3]}/")
        if nxt is not None and not vendor:
            vendor = nxt.parts[-3]
        cur = nxt
    return out


def flat_val(v):
    return v[0] if isinstance(v, list) and v else v


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    kind = "process" if "--process" in sys.argv else "filament"
    default = ("TPU 95A Default @Kobra 2 Neo" if kind == "process"
               else "Elegoo PLA Calibrated @Kobra 2 Neo")
    target = args[0] if args else default

    by_vendor, flat = index_system(kind)
    dups = {}
    for (v, n) in by_vendor:
        dups.setdefault(n, []).append(v)
    colisiones = {n: vs for n, vs in dups.items() if len(vs) > 1}

    print(f"Tipo: {kind}   |   perfiles de sistema: {len(flat)}")
    if colisiones:
        print(f"Nombres presentes en varias marcas: {len(colisiones)}"
              f"  (ej. {list(colisiones)[0]})")
    print()

    p = preset_dir(kind) / f"{target}.json"
    if not p.exists():
        sys.exit(f"No existe: {p}")

    # el fabricante arranca del 'inherits' del perfil de usuario
    first = json.loads(p.read_text())
    parent = first.get("inherits")
    vendor = None
    if parent:
        cands = [v for (v, n) in by_vendor if n == parent]
        vendor = cands[0] if len(cands) == 1 else (cands[0] if cands else None)
        if len(cands) > 1:
            print(f"[aviso] '{parent}' existe en {cands}; se usa {vendor}\n")

    ch = chain(p, by_vendor, flat, vendor)
    print("Cadena de herencia:")
    for i, (n, _, ven) in enumerate(ch):
        print(f"   {'  ' * i}{'^- ' if i else ''}{n}   [{ven}]")
    print()

    print(f"{'campo':<28}{'efectivo':>14}   proviene de")
    print("-" * 78)
    for c in CAMPOS[kind]:
        val, src = "<default interno>", "-"
        for n, d, _ in ch:
            if c in d:
                val, src = flat_val(d[c]), ("PROPIO" if n == ch[0][0] else n)
                break
        print(f"{c:<28}{str(val):>14}   {src}")


if __name__ == "__main__":
    main()
