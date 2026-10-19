# Fabricación del lote 1 de frames (S10-06)

Lote 1 = las piezas de los prototipos aprobados en el G2 (fase B del BOM). Proceso y perfiles:
[piezas_frame.md](../../../manufacturing/procesos/piezas_frame.md). Archivos: `cad/exports/{inspection,delivery}/`.

## Antes de mandar a fabricar

1. Regenerar todo desde la fuente: `tools/cad/gen_cad_params.py` y `tools/cad/build_frame.py inspection|delivery`,
   con 0 interferencias.
2. Ajustar holguras con **una impresión de prueba**: un bloque de brazo con un trozo de tubo real. Si el ajuste está
   flojo o duro, cambiar la holgura del agujero en `cad/openscad/common/ds_lib.scad` (+0.2 a +0.3 mm) y regenerar.
3. Probetas de tracción del lote de filamento (`piezas_frame.md` §2) **antes** de imprimir piezas de vuelo.

## Registro del lote (llenar al recibir)

| Pieza | Dron | Cant. | Masa esperada (CAD) | Masa medida | Medidas críticas OK | Orientación / perfil usado | Proveedor | Observaciones |
|---|---|---|---|---|---|---|---|---|
| Placa central inferior | DS-I | 1 | 98 g | | | CNC | | |
| Placa central superior | DS-I | 1 | 102 g | | | CNC | | |
| Bloque de brazo | DS-I | 4 | 18 g | | | | | |
| Soporte de motor DMI-S | DS-I | 4 | 15 g | | | | | |
| Abrazadera de pata | DS-I | 4 | 11 g | | | | | |
| Pie amortiguador (TPU) | DS-I | 4 | 9 g | | | | | |
| Bandeja de batería | DS-I | 1 | 38 g | | | | | |
| Adaptador de cámara sup./inf. | DS-I | 2 | 14 / 21 g | | | | | |
| Carcasa IP54 | DS-I | 1 | 78 g | | | | | |
| Placa central inferior | DS-D | 1 | 435 g | | | CNC | | |
| Placa central superior | DS-D | 1 | 450 g | | | CNC | | |
| Bloque desmontable | DS-D | 6 | 37 g | | | | | |
| Soporte de motor DMI-L | DS-D | 6 | 30 g | | | | | |
| Gancho de carga (aluminio) | DS-D | 1 | 18 g | | | corte por agua | | |
| Cuerpo de liberación | DS-D | 1 | 70 g | | | | | |
| Resto (bandeja, carcasa, tren, FPV, luces) | DS-D | — | ver `cad/exports/delivery/masas.json` | | | | | |

Si la masa total del frame supera en más de 10 % la del CAD, se avisa antes de ensamblar: cambia la autonomía.
