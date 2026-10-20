# Valores de fabricación y control de calidad

> Generado por `motor/fabricacion/gen_valores.py` desde el diseño (M2), la FEM (M4), M5 y el CAD (M6). No editar a mano.

| | DS-I | DS-D |
|---|---|---|
| Ranuras / polos | 24N26P | 36N32P |
| Estator | Ø43.9 mm × 6.2 mm, 29 láminas de 0.20 mm | Ø69.7 mm × 8.4 mm, 40 láminas de 0.20 mm |
| Anillo del rotor | 9 anillos de 1.0 mm, Ø49.5 mm | 11 anillos de 1.0 mm, Ø77.6 mm |
| Imanes | 26 imanes N48SH de 4.6 × 6.2 × 1.0 mm (ancho × largo × espesor, magnetizados en el espesor) | 32 imanes N48SH de 5.9 × 8.4 × 1.5 mm (ancho × largo × espesor, magnetizados en el espesor) |
| Bobinado | 8 vueltas por diente, 1 × Ø0.60 mm (cobre +2 % del diseño), estrella | 6 vueltas por diente, 7 × Ø0.32 mm en paralelo (cobre +2 % del diseño), estrella |
| Orden de las bobinas (diente 1 → n) | `AacCcCBbBbaAaACcCcbBbBAa` (mayúscula = un sentido, minúscula = el contrario) | `AabBbcCcaAabBbcCcaAabBbcCcaAabBbcCca` (mayúscula = un sentido, minúscula = el contrario) |
| **Resistencia fase-fase a 20 °C** | **159 mΩ** (las 3 iguales ± 3 %) | **113 mΩ** (las 3 iguales ± 3 %) |
| **Kv esperado** | **324-332 rpm/V** (FEM 2D / cálculo; el real suele quedar más cerca del mayor) | **127 rpm/V** |
| Corriente en vacío a 22 V (DS-I) / 44 V (DS-D) | se registra en el primer motor (referencia para el resto) | se registra en el primer motor (referencia para el resto) |
| Masa esperada | 80 g | 241 g |
| Bobinado a empuje máximo continuo (M5) | 51 °C (límite 120 °C) | 96 °C (límite 120 °C) |
