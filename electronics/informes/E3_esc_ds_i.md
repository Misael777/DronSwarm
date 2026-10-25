# E3 · ESC 4 en 1 del DS-I: ¿GaN, silicio propio o comercial?

> Generado por `electronics/calculo/esc_ds_i_decision.py`. Precios de materiales estimados a 100 unidades (se cotizan en E7).

Requisitos (E0): bus 6S 21.6 V (máx. 25.2 V), 5.46 A por motor en hover, 10.5 A continuos y 13.8 A de pico de diseño, 4 motores.

| | Silicio propio | GaN propio | Comercial |
|---|---|---|---|
| Transistor | CSD18503Q5A (Si 40 V, SON 5×6) | EPC2302 (GaN 100 V, QFN 3×5) | 40 V (no publicado) |
| Conmutación | 24 kHz | 48 kHz | 24-48 kHz |
| Pérdida por motor: hover / maniobra / pico [W] | 0.48 / 0.96 / 1.59 | 0.21 / 0.4 / 0.64 | — |
| Eficiencia del ESC en hover | 99.31 % | 99.70 % | — |
| Costo de materiales de la placa 4 en 1 | **US$43** | US$159 | US$80 |

**GaN contra silicio en el DS-I:** ahorra 1.08 W en hover (0.39 % de la potencia) y cuesta US$117 más por dron. No se justifica: con 6S y ~5 A por motor el silicio ya está por encima del 99 %.

**Decisión: Silicio propio.** El 4 en 1 de silicio propio cuesta ~US$43 contra US$80 del comercial, usa el mismo firmware (AM32, STM32G071) y la misma estructura que el ESC del DS-D (medición de corriente por motor, contra-FEM, protecciones), y permite ajustar la conmutación a nuestros motores de baja inductancia. El GaN queda para el DS-D (E1/E2) y el cargador.

## Materiales por canal (silicio)

- CSD18503Q5A ×6: US$3.30
- DRV8300DPW (driver trifásico, bootstrap integrado): US$0.85
- STM32G071KBU6N: US$1.60
- Shunt 1 mΩ 2512 + INA181A3: US$0.60
- Pasivos (divisores, desacople, filtros): US$0.90

## Materiales comunes de la placa

- LM5164 + inductor (12 V para los drivers): US$1.85
- MCP1703 3.3 V: US$0.35
- Condensadores del bus (2 × 470 µF 35 V + MLCC): US$1.30
- TVS SMAJ26A + ESD de señales: US$0.70
- Conectores (JST-GH 6 pines, pads): US$0.60
- PCB 4 capas 2 oz 50 × 50 mm: US$3.00
- Montaje SMD por servicio (por placa): US$6.00
