# archive/ — scripts retirados

Nada de aquí debe ejecutarse. Se conserva por trazabilidad histórica.

| Archivo | Por qué está aquí |
|---|---|
| `generate_processes.py.VETADO` | Destruyó 23 parámetros el 2026-07-31. Extensión `.VETADO` para que `python3` no lo corra por accidente. Ver abajo. |
| `restore_processes.py` | Script de un solo uso para recuperarse de ese incidente. Su glob apunta a backups del `20260731_1312`. **Correrlo hoy revertiría todo el trabajo posterior.** |
| `apply_patch.py` | Ya aplicado. El parche vive dentro de `generate_profiles.py`. Correrlo dice "ya está parcheado" y no hace nada. |
| `export_processes.py` | Reemplazado por `snapshot_orca.py`, que además cubre filamentos y máquina, detecta el UUID solo y tiene `--diff`. |
| `processes.yaml` | **Sus valores no coinciden con el disco en 13 campos.** Se conserva solo por los comentarios de diseño. No es configuración. |
| `PROCESOS.md` | Último export de `export_processes.py` (2026-07-31). Sustituido por `CONFIGURACION.md`. |

## Los cuatro bugs de `generate_processes.py`

Verificados leyendo `build_orca_process()`:

1. **`sparse_infill_density: [f"{s['...']}%"]`** — el YAML ya trae `"15%"`, así que escribe `15%%`.
2. **`s.get("elephant_foot_compensation")`** con dos `f`, pero el YAML usa `elefant_foot_compensation` con una. Nunca encuentra el valor; siempre escribe el default.
3. **`seam = s.get("seam", {})`** espera un bloque anidado con `position`/`gap`. El YAML tiene `seam_position` y `seam_gap` planos. Resultado: siempre escribe `aligned`, y **descarta los ~7 campos de scarf seam** porque `seam.get("scarf")` es falso.
4. **`s.get("enable_support")`** dentro de `settings`, pero el YAML tiene `support:` a nivel de ítem. Los ~12 parámetros de soporte se pierden en cada regeneración.

Arreglarlo exige ~45 campos más en el builder. No vale la pena: los procesos se ajustan en la UI y se versionan con `snapshot_orca.py`.
