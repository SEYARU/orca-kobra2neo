#!/usr/bin/env python3
"""
snapshot_orca.py
==============================================================================
Captura COMPLETA y READ-ONLY de la configuración de usuario de OrcaSlicer:
filamentos, procesos y máquina.

REEMPLAZA a export_processes.py (que solo cubría procesos). Bórralo después
de verificar que este corre bien, o terminarás con dos fuentes de verdad.

GARANTÍA DE DISEÑO
    Este script NO tiene una sola llamada de escritura sobre el directorio
    de OrcaSlicer. Solo lee de ahí y escribe dentro de su propia carpeta de
    proyecto. Es imposible que corrompa un preset.

QUÉ HACE
    snapshots/<timestamp>/       copia literal de cada JSON
    CONFIGURACION.md             tablas legibles de todo, para git
    --diff                       compara el estado ACTUAL contra el último
                                 snapshot y lista campo por campo lo que
                                 cambiaste a mano en la UI

FLUJO CON EDICIÓN MANUAL
    1. python3 snapshot_orca.py            # línea base ANTES de tocar nada
    2. ...editas en la UI de OrcaSlicer y guardas los presets...
    3. python3 snapshot_orca.py --diff     # ¿qué cambió realmente?
    4. python3 snapshot_orca.py            # congelar el nuevo estado
    5. git add -A && git commit

USO
    python3 snapshot_orca.py
    python3 snapshot_orca.py --diff
    python3 snapshot_orca.py --diff --against 20260809_014057
    python3 snapshot_orca.py --list
==============================================================================
"""

import json
import shutil
import sys
from pathlib import Path
from datetime import datetime

PROJECT = Path(__file__).resolve().parent
SNAP_ROOT = PROJECT / "snapshots"
MD_FILE = PROJECT / "CONFIGURACION.md"

from orca_paths import ORCA_ROOT, ORCA_USER, KINDS as _K, account_dir

KINDS = list(_K)

# Campos de ruido: cambian solos y ensucian los diffs sin aportar nada.
NOISE = {"from", "instantiation", "is_custom_defined", "version", "setting_id"}


# ---------------------------------------------------------------------------
def resolve_orca_dir() -> Path:
    acc = account_dir()
    print(f"✅ Cuenta detectada: {acc.name}")
    return acc


def read_presets(base: Path) -> dict:
    """{kind: {nombre: dict}} — lectura pura, nada se escribe."""
    out = {}
    for kind in KINDS:
        folder = base / kind
        if not folder.is_dir():
            continue
        out[kind] = {}
        for f in sorted(folder.glob("*.json")):
            try:
                out[kind][f.stem] = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON inválido, se omite: {f.name} ({e})")
    return out


def orca_version() -> str:
    """Versión de OrcaSlicer desde el Info.plist de la app, si está."""
    for p in [Path("/Applications/OrcaSlicer.app/Contents/Info.plist"),
              Path.home() / "Applications/OrcaSlicer.app/Contents/Info.plist"]:
        if p.is_file():
            txt = p.read_text(errors="ignore")
            key = "<key>CFBundleShortVersionString</key>"
            if key in txt:
                tail = txt.split(key, 1)[1]
                if "<string>" in tail:
                    return tail.split("<string>", 1)[1].split("</string>", 1)[0].strip()
    return "desconocida"


# ---------------------------------------------------------------------------
def write_snapshot(base: Path, data: dict) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = SNAP_ROOT / stamp
    total = 0
    for kind in data:
        (dest / kind).mkdir(parents=True, exist_ok=True)
        for name in data[kind]:
            shutil.copy2(base / kind / f"{name}.json", dest / kind / f"{name}.json")
            total += 1
    (dest / "_meta.json").write_text(json.dumps({
        "timestamp": stamp,
        "orcaslicer_version": orca_version(),
        "account_uuid": base.name,
        "preset_count": total,
    }, indent=2), encoding="utf-8")
    print(f"📦 Snapshot: snapshots/{stamp}  ({total} presets)")
    return dest


def write_markdown(data: dict, base: Path):
    L = [
        "# Configuración OrcaSlicer — Anycubic Kobra 2 Neo",
        "",
        f"Generado: {datetime.now():%Y-%m-%d %H:%M}  ",
        f"OrcaSlicer: {orca_version()}  ",
        f"Cuenta: `{base.name}`",
        "",
        "> Documento generado por `snapshot_orca.py`. **No editar a mano** —",
        "> se sobrescribe en cada corrida. Edita en la UI de OrcaSlicer y",
        "> vuelve a ejecutar el script.",
        "",
    ]
    titles = {"filament": "Filamentos", "process": "Procesos", "machine": "Máquina"}
    for kind in KINDS:
        if not data.get(kind):
            continue
        L += [f"## {titles[kind]}", ""]
        for name, d in sorted(data[kind].items()):
            L += [f"### {name}", ""]
            if d.get("inherits"):
                L += [f"Hereda de: `{d['inherits']}`", ""]
            L += ["| Campo | Valor |", "|---|---|"]
            for k in sorted(d):
                if k in NOISE or k in ("name", "inherits"):
                    continue
                v = d[k]
                if isinstance(v, list):
                    v = ", ".join(map(str, v)) if len(v) <= 6 else f"[{len(v)} valores]"
                v = str(v).replace("|", "\\|").replace("\n", "<br>")
                if len(v) > 300:
                    v = v[:300] + " …(truncado)"
                L += [f"| `{k}` | {v} |"]
            L += [""]
    MD_FILE.write_text("\n".join(L), encoding="utf-8")
    print(f"📄 {MD_FILE.name}")


# ---------------------------------------------------------------------------
def load_snapshot(path: Path) -> dict:
    out = {}
    for kind in KINDS:
        folder = path / kind
        if folder.is_dir():
            out[kind] = {
                f.stem: json.loads(f.read_text(encoding="utf-8"))
                for f in sorted(folder.glob("*.json"))
            }
    return out


def diff(current: dict, previous: dict, ref: str):
    print(f"\n🔬 ACTUAL  vs  snapshots/{ref}\n")
    found = False
    titles = {"filament": "FILAMENTO", "process": "PROCESO", "machine": "MÁQUINA"}

    for kind in KINDS:
        cur, old = current.get(kind, {}), previous.get(kind, {})

        for name in sorted(set(cur) - set(old)):
            print(f"   ➕ {titles[kind]} nuevo: {name}"); found = True
        for name in sorted(set(old) - set(cur)):
            print(f"   ➖ {titles[kind]} borrado: {name}"); found = True

        for name in sorted(set(cur) & set(old)):
            a, b = cur[name], old[name]
            keys = (set(a) | set(b)) - NOISE
            rows = [
                (k, b.get(k, "⟨ausente⟩"), a.get(k, "⟨borrado⟩"))
                for k in sorted(keys)
                if a.get(k, "⟨borrado⟩") != b.get(k, "⟨ausente⟩")
            ]
            if not rows:
                continue
            found = True
            print(f"   📝 {titles[kind]}: {name}")
            for k, o, n in rows:
                o, n = str(o)[:40], str(n)[:40]
                print(f"      {k:<32} {o:>18}  ->  {n}")
            print()

    if not found:
        print("   ✓ Sin diferencias. Lo que ves en OrcaSlicer es lo versionado.\n")


def list_snapshots():
    if not SNAP_ROOT.is_dir():
        sys.exit("Sin snapshots todavía.")
    for d in sorted(SNAP_ROOT.iterdir()):
        meta = d / "_meta.json"
        if meta.is_file():
            m = json.loads(meta.read_text())
            print(f"   {d.name}   Orca {m['orcaslicer_version']:<8} {m['preset_count']} presets")
        else:
            print(f"   {d.name}")


# ---------------------------------------------------------------------------
def main():
    args = sys.argv[1:]

    if "--list" in args:
        list_snapshots()
        return

    base = resolve_orca_dir()
    current = read_presets(base)
    n = sum(len(v) for v in current.values())
    if n == 0:
        sys.exit("❌ No se encontró ningún preset de usuario.")
    print(f"   Leídos: " + ", ".join(f"{len(v)} {k}" for k, v in current.items() if v))

    if "--diff" in args:
        if "--against" in args:
            ref = args[args.index("--against") + 1]
            path = SNAP_ROOT / ref
            if not path.is_dir():
                sys.exit(f"❌ No existe snapshots/{ref}")
        else:
            snaps = sorted(d for d in SNAP_ROOT.iterdir() if d.is_dir()) if SNAP_ROOT.is_dir() else []
            if not snaps:
                sys.exit("❌ No hay snapshot previo. Corre sin --diff primero.")
            path, ref = snaps[-1], snaps[-1].name
        diff(current, load_snapshot(path), ref)
        return

    write_snapshot(base, current)
    write_markdown(current, base)
    print("\n✅ Listo. `git add -A && git commit -m \"snapshot config\"`")


if __name__ == "__main__":
    main()
