# OrcaSlicer Profile Manager — Anycubic Kobra 2 Neo

Gestión declarativa y versionable de perfiles de OrcaSlicer.

**Alcance:** los **filamentos** se generan desde YAML. Los **procesos** se editan
en la UI de OrcaSlicer y se versionan con snapshots. Esa asimetría es
deliberada — ver [`archive/README.md`](archive/README.md).

---

## Instalación

```bash
git clone <tu-repo> ~/Documents/orca-kobra2neo
cd ~/Documents/orca-kobra2neo
pip3 install -r requirements.txt
python3 orca_paths.py          # verifica que detecte tu cuenta
```

Salida esperada:

```
✅ Cuenta detectada: ba9291fb-…
   filament   3 preset(s)
   process    3 preset(s)
   machine    1 preset(s)
```

Si dice que no encuentra la cuenta, inicia sesión en OrcaSlicer y reintenta.

---

## Estado: 3 × 3

| Filamento (desde YAML) | Proceso (a mano) | Estado |
|---|---|---|
| `Elegoo PLA @Kobra 2 Neo` | `PLA Default @Kobra 2 Neo` | Calibrado |
| `Elegoo PLA Wood @Kobra 2 Neo` | `PLA Wood Default @Kobra 2 Neo` | Preliminar |
| `Elegoo TPU 95A Black @Kobra 2 Neo` | `TPU 95A Default @Kobra 2 Neo` | Calibrado |

---

## Scripts

| Script | Qué hace | Escribe en OrcaSlicer |
|---|---|---|
| `orca_paths.py` | Módulo compartido: localiza la carpeta de cuenta | No |
| `generate_profiles.py` | Genera filamentos desde `filaments.yaml` | Sí (con backup) |
| `snapshot_orca.py` | Captura y versiona TODA la config · `--diff` | **No — read-only** |
| `patch_skirt_242.py` | Ajusta skirt en los procesos, sin reconstruirlos | Sí (con backup) |
| `retire_presets.py` | Retira presets viejos · `--restore` | Sí (reversible) |
| `cleanup.py` | Limpia backups y papeleras del proyecto | No |

Todos aceptan `--dry-run`. Úsalo siempre primero.

---

## Flujos

### Calibrar un filamento

```bash
python3 snapshot_orca.py                    # línea base
# editar filaments.yaml: 2-3 valores + calibrated: true
python3 generate_profiles.py --dry-run
python3 generate_profiles.py
# Cmd+Q COMPLETO en OrcaSlicer y reabrir
python3 snapshot_orca.py && git commit -am "calibrar X"
```

### Ajustar un proceso

```bash
python3 snapshot_orca.py                    # línea base — no lo saltes
# ...editar en la UI de OrcaSlicer y GUARDAR cada preset...
# Cmd+Q COMPLETO
python3 snapshot_orca.py --diff             # ¿qué cambió de verdad?
python3 snapshot_orca.py && git commit -am "ajustar procesos"
```

El `--diff` existe porque editar a mano falla en silencio: crees que
guardaste y cambiaste el preset activo sin persistirlo. El diff lee el disco,
no tu memoria.

---

## Contrato de `generate_profiles.py`

`build_orca_profile()` accede con corchete (`s["x"]`): **falta una clave =
KeyError y el filamento no se genera.**

**Settings obligatorios (14):**

```
nozzle_temp   first_layer_temp   bed_temp   first_layer_bed
flow_ratio    max_volumetric_speed          pressure_advance
retraction    retraction_speed   z_hop
fan_speed     min_layer_time     min_print_speed
disable_fan_first_layers
```

**Nivel de ítem** (fuera de `settings`): `name`, `type` obligatorios ·
`vendor`, `color`, `calibrated` opcionales.

**`printer.inherit_base`** es un dict indexado por `type`.

---

## Trampas conocidas

**Los bases genéricos de marca no funcionan.** `Anycubic Generic PLA` hace que
OrcaSlicer registre el perfil pero lo **filtre del dropdown**. Hay que heredar
de un base específico de impresora — en esta instalación solo existe uno:

```
Anycubic PLA @Anycubic Kobra 2 Neo 0.4 nozzle
```

El TPU también hereda de ese base de PLA. Lo que se hereda es la
**compatibilidad con la impresora**, no los parámetros del material.

**Cierra OrcaSlicer antes de tocar archivos.** Con el slicer abierto, al
cerrarse vuelca sus presets en memoria al disco y recrea lo que borraste. No
es sync ni nube: es orden de eventos.

**Los `.info` acompañan a los `.json`.** Al mover o borrar presets, mueve el
par completo.

**`pgrep -f` da falsos positivos.** Busca en la línea de comandos completa, así
que un shell con `ORCA="…OrcaSlicer…"` cuenta como el slicer corriendo. Usar
`pgrep -x OrcaSlicer`.

**Campos desconocidos se descartan en silencio.** El builder arma el dict campo
por campo. Clave nueva en el YAML sin su línea en el builder = nada pasa y no
te enteras.

**`compatible_prints_condition` va como string plano**, no como lista. El resto
va en lista porque OrcaSlicer los trata como vectores por extrusor.

**`elefant_foot_compensation` con una sola `f`.** Nombre exacto del campo en el
JSON. No es un typo.

**Mover archivos NO borra un preset.** `retire_presets.py` los saca de la
carpeta, pero OrcaSlicer sigue teniendolos en memoria y los repone al
cerrar. Hicieron falta tres tandas en `_retirados/` para descubrirlo. Para
eliminar de verdad: abrir OrcaSlicer, seleccionar el preset, boton de
quitar preset (el icono junto al disquete), confirmar, y Cmd+Q completo.
`retire_presets.py` sirve para limpiar restos con el slicer cerrado, no
para eliminar presets que el slicer conoce.

**`compatible_prints_condition` NO funciona.** El PLA Wood lo declara
(`print_preset_name =~ /.*Wood.*/`) y OrcaSlicer 2.4.2 lo ignora: permite
seleccionar Wood con el proceso `PLA Default` sin avisar. La documentacion
apenas cubre este campo. **No importa**: medido sobre G-code real, el freno
efectivo es `max_volumetric_speed: 8` en el FILAMENTO. Con `PLA Default`
pidiendo 120 mm/s de relleno, el resultado fue 100.3 mm/s (8.0 mm3/s) — el
slicer recorto un 16%. La proteccion es fisica, no declarativa.

**`system/` tiene nombres duplicados entre fabricantes.**
`fdm_process_common` existe en `Anycubic/` y en `Custom/` con valores
distintos: el de Custom declara `min_skirt_length: 4`, el de Anycubic no lo
declara. Cualquier script que indexe `system/` por nombre de archivo
resolverá contra la marca equivocada y reportará un valor que no es el tuyo.
Indexar siempre por `(fabricante, nombre)` — ver `resolve_inherited.py`.

**Un script read-only no puede romper nada, pero sí puede mentir.** Ese bug
metió un número inventado en un diagnóstico y estuvo a punto de guiar una
decisión. Medir antes de optimizar exige también verificar el instrumento.

**Aceleración = 2000, no 2500.** Límite real de la Kobra 2 Neo; 2500 es la
Kobra 2 a secas.

**Nada de `/` en nombres de preset.** El nombre se vuelve nombre de archivo.

---

## Valores calibrados

**No cambiar sin recalibrar.**

| | PLA | PLA Wood | TPU 95A |
|---|---|---|---|
| Nozzle | 210 / 215 | 215 / 220 | 220 / 225 |
| Cama | 60 / 65 | 60 / 65 | 50 / 55 |
| `flow_ratio` | 1.0 | 0.98 | 1.1 |
| `max_volumetric_speed` | 15 | **8** | 5 |
| `retraction` | 0.5 @ 40 | 0.5 @ 25 | 1.5 @ 30 |
| `fan_speed` | 100 | 100 | **30** |
| `pressure_advance` | 0 (off) | 0 (off) | 0 (off) |

El ventilador del TPU a 30% es deliberado: más aire mata la adhesión entre
capas. El `max_volumetric_speed` del wood en 8 es la única defensa real contra
el atasco.

---

## Skirt (OrcaSlicer 2.4.x)

Valores aplicados por `patch_skirt_242.py`:

| Campo | PLA | PLA Wood | TPU 95A |
|---|---|---|---|
| `skirt_loops` | 1 | 2 | 3 |
| `skirt_distance` | 2 | 2 | 3 |
| `skirt_speed` | 0 (hereda 1ª capa) | 20 | 15 |
| `min_skirt_length` | 0 | 0 | 0 |
| `draft_shield` | disabled | disabled | disabled |

`min_skirt_length` en 0 porque la Kobra ya purga en el start G-code. Con un
valor distinto de cero, OrcaSlicer añade vueltas hasta alcanzar esa longitud
**ignorando `skirt_loops`** — la causa más común de "demasiado sobrante".

El brim no se fija en el preset: se activa por objeto (clic derecho en la
placa) cuando la base es estrecha. `brim_object_gap: 0.1` ya está calibrado
para que se desprenda limpio.

---

## Secado

| Material | Temp | Tiempo | Nota |
|---|---|---|---|
| PLA / PLA+ | 50 °C | 6 h | Post-impresión no aporta |
| PLA Wood | **50 °C máx** | 4 h | Más calor degrada la fibra |
| TPU 95A | 65 °C | 8 h | Post-impresión: 45 min |

Space Pi SE: 24 h máximo por ciclo, sin modo continuo. Mantenimiento diario:
24 h / 45 °C. Ambiente de 70-85 % RH.

---

## Ruteo de filamento

El estante de las SE con recorrido de 45 cm funciona para PLA y TPU.

**No para PLA Wood.** El material es frágil y se quiebra dentro del bowden,
dejando un fragmento suelto que el extrusor empuja sin resultado — el síntoma
de "no sale filamento pero la impresora sigue imprimiendo". Para wood: carrete
abajo, alimentación directa. Antes de cargarlo, purga el bowden empujando PLA
normal.

---

## Criterio de consolidación

**Filamento = qué le metes. Proceso = cómo se mueve la máquina.**

Fusionar cuando `flow_ratio` difiere < 2 % (el ruido de la tolerancia
±0.02 mm) y `pressure_advance` es idéntico. Separar cuando
`max_volumetric_speed` o `retraction` difieren: son límites físicos, no
preferencias.

PLA+ y PLA gris se fusionaron. El Wood no (caudal 8 vs 15).

---

## Lección de fondo

Los perfiles que ya funcionan en disco son la fuente de verdad. En su momento
se inventaron valores de `flow_ratio`, `retraction`, `fan_speed` y
`pressure_advance` para dos filamentos que **ya estaban calibrados**, y sobre
uno de esos errores se construyó un consejo técnico completo.

El mismo patrón produjo un `processes.yaml` que divergía del disco en 13
campos mientras se presentaba como documentación. Está en `archive/`.

Antes de escribir un perfil: leer el que ya existe.
