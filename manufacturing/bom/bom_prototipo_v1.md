# BOM del prototipo v1 · resumen

> Generado por `tools/bom/gen_bom.py` desde la selección COTS. Detalle línea por línea en `bom_prototipo_v1.csv` (cantidades, precios, fase de compra, plazos, 2 proveedores por ítem). Los precios marcados como estimados se reemplazan con las cotizaciones del S10.

**Para revisar y seguir las compras:** `Lista_de_Compras_Prototipo_v1.xlsx` (resumen, compras con estado y cotizaciones, lista de armado de cada dron), generado por `tools/bom/gen_bom_xlsx.py`.

## Costo por dron (sin repuestos ni equipo de tierra)

| | Prototipo v1 (componentes de marca, compra unitaria) | Presupuesto del S04 | Diferencia |
|---|---|---|---|
| DS-I | US$1,865 | US$735 | +154% |
| DS-D | US$4,080 | US$1,627 | +151% |

## Flota de prototipos (4 DS-I + 2 DS-D), repuestos y equipo

| Categoría | Total |
|---|---|
| propulsión | US$5,985 |
| aviónica | US$6,230 |
| batería | US$2,320 |
| frame y kits | US$1,964 |
| equipo de tierra y banco | US$1,250 |
| **Total** | **US$17,749** |

**Fase A (validación, pedir ya):** ≈ US$3,855. Incluye baterías, cargadores, banco de empuje, 2 motores de cada tipo, 1 ESC de cada tipo y hélices. **Fase B (flota):** el resto, cuando el banco confirme los motores (S10).

## Por qué el prototipo cuesta más que el objetivo

- **Motores de marca a precio unitario:** US$75-170 cada uno, contra US$18-56 del modelo paramétrico del S04, que suponía precio de fábrica en volumen. Este es el hueco que cierra el motor propio (S17-S19).
- **Aviónica de desarrollo:** Pixhawk 6C, GNSS RTK multibanda, computadora a bordo y una radio por dron. En producción, el DS-I base no lleva RTK ni computadora (escenario D) y la controladora puede ser propia (S20-S21).
- **Frame en servicios por pieza:** imprimir en casa y cortar placas por lote baja ~40 % el costo del frame.
- El costo de producción se recalcula en el S24 con volumen de 100 unidades, motor y electrónica propios.
