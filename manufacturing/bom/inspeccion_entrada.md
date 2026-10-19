# Compras e inspección de entrada (S10-01)

- Qué comprar: [bom_prototipo_v1.md](bom_prototipo_v1.md) (fase A primero) · Seguimiento: `seguimiento_compras.csv`
  (lo llenas tú; `tools/bom/gen_bom.py` lo crea una sola vez y nunca lo sobrescribe).
- Regla: **nada se instala sin pasar la inspección de entrada.** Lo rechazado se anota en `observaciones` y se reclama.

## Seguimiento

1. Al pedir: proveedor elegido, precio real, fecha de pedido y fecha estimada.
2. Al llegar: fecha de llegada, inspección (sí/no) y observaciones.
3. Las celdas y baterías viajan como **mercancía peligrosa (UN3480)**. Confirmar con el proveedor el modo de envío y el
   plazo (aéreo de carga o marítimo); es lo que más se demora.
4. Si un precio real se aleja más de 15 % del BOM, actualizar el precio en `engineering/cots.py` y regenerar el BOM
   (`tools/bom/gen_bom.py`): el resumen de costos se recalcula solo.

## Criterios de inspección por tipo

| Ítem | Inspección | Criterio de aceptación |
|---|---|---|
| Motores | Giro a mano (sin roce ni juego axial), eje y seguro, medida de resistencia entre fases | Resistencia entre fases = 2 × Rm del catálogo ± 15 %; iguales entre motores ± 5 % |
| Motores (2 de cada lote) | Ensayo `noload` en el banco | Kv ± 5 % del catálogo |
| ESC | Firmware (BLHeli32/AM32), configuración de telemetría y DShot | Telemetría de corriente funcionando en el banco |
| Celdas 21700 | Voltaje y resistencia interna (probador de 4 hilos) de una muestra de 10 % | Voltaje 3.5-3.7 V de despacho; RI ≤ 1.3 × la de la hoja de datos. Si una falla, se mide el 100 % |
| Packs armados | Voltaje de cada serie, prueba de carga a 1C con cámara térmica | Desbalance ≤ 20 mV; ningún punto caliente > 10 °C sobre el promedio |
| Placas de carbono | Espesor en 5 puntos, planitud, agujeros con calibre M3/M4 | 3.0 ± 0.15 mm; planitud ≤ 0.3 mm; sin delaminación en los bordes |
| Tubos de carbono | Diámetro exterior, ovalidad, largo | ± 0.1 mm en el diámetro (ajuste en los bloques); largo ± 0.5 mm |
| Piezas impresas | Masa y medidas críticas (agujeros del tubo con un tubo de prueba) | Masa ± 10 % de `cad/exports/*/masas.json`; el tubo entra a mano sin juego visible |
| Controladora, GNSS y radios | Encendido, firmware, número de serie anotado | Arranca y es reconocida por QGroundControl |
