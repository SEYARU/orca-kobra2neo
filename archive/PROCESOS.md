# Process Presets — Anycubic Kobra 2 Neo

Exportado: 2026-07-31 14:04

> Generado por `export_processes.py`. **No editar a mano.**
> Los procesos se ajustan en la UI de OrcaSlicer; después se
> re-exporta este archivo. `generate_processes.py` está vetado:
> su builder borra soportes y scarf seam al regenerar.

## Comparativa

| Parámetro | PLA Default | PLA Wood Default | TPU 95A Default |
|---|---|---|---|
| Altura de capa | 0.2 | 0.2 | 0.2 |
| Altura 1ª capa | 0.2 | 0.2 | 0.2 |
| Paredes | 3 | 3 | 3 |
| Capas superiores | 5 | 5 | 4 |
| Capas inferiores | 4 | 4 | 4 |
| Relleno | 15% | 15% | 15% |
| Patrón relleno | gyroid | gyroid | gyroid |
| Brim | 5 | 5 | 5 |
| Pared exterior | 30 | 30 | 20 |
| Pared interior | 80 | 45 | 25 |
| Relleno (vel.) | 120 | 50 | 30 |
| Superficie sup. | 40 | 30 | 20 |
| 1ª capa (vel.) | 20 | 20 | 15 |
| Viaje | 150 | 150 | 100 |
| Aceleración | 2000 | 2000 | 1000 |
| Acel. pared ext. | 1000 | 1000 | 500 |
| Costura | back | back | back |
| Tipo soporte | normal(auto) | normal(auto) | normal(auto) |
| Soporte Z sup. | 0.2 | 0.2 | 0.25 |
| Soporte XY | 0.35 | 0.35 | 0.4 |

## PLA Wood Default — diferencias vs PLA Default

| Campo | PLA | Este |
|---|---|---|
| `inner_wall_speed` | 80 | 45 |
| `internal_solid_infill_speed` | — | 50 |
| `line_width` | — | 0.45 |
| `outer_wall_line_width` | — | 0.45 |
| `sparse_infill_speed` | 120 | 50 |
| `top_surface_speed` | 40 | 30 |

## TPU 95A Default — diferencias vs PLA Default

| Campo | PLA | Este |
|---|---|---|
| `default_acceleration` | 2000 | 1000 |
| `initial_layer_speed` | 20 | 15 |
| `inner_wall_speed` | 80 | 25 |
| `outer_wall_acceleration` | 1000 | 500 |
| `outer_wall_speed` | 30 | 20 |
| `sparse_infill_speed` | 120 | 30 |
| `support_bottom_z_distance` | 0.2 | 0.25 |
| `support_interface_spacing` | 0.5 | 0.6 |
| `support_object_xy_distance` | 0.35 | 0.4 |
| `support_threshold_angle` | 40 | 45 |
| `support_top_z_distance` | 0.2 | 0.25 |
| `top_shell_layers` | 5 | 4 |
| `top_surface_speed` | 40 | 20 |
| `travel_speed` | 150 | 100 |

## Campos por preset

- **PLA Default @Kobra 2 Neo** — 52 campos · support (11), seam (8), sparse (3), brim (3), scarf (3), initial (2)
- **PLA Wood Default @Kobra 2 Neo** — 55 campos · support (11), seam (8), sparse (3), outer (3), brim (3), scarf (3)
- **TPU 95A Default @Kobra 2 Neo** — 52 campos · support (11), seam (8), sparse (3), brim (3), scarf (3), initial (2)
