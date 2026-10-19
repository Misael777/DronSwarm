# Gate G2 · Revisión de diseño crítico del prototipo (CDR)

- Sprint: S09 · Tarea: S09-07
- Estado: **Pendiente de aprobación del equipo**. Recomendación: **aprobar la compra de la fase A (validación)** y decidir el tamaño de la flota (sección 4).
- Fecha de preparación: 2026-10-19
- Depende de los Gates **G0 y G1, que siguen abiertos**: este diseño usa los escenarios recomendados D (DS-I) y C (DS-D).

## Criterio del gate (plan)
Frame (OpenSCAD + ensamble FreeCAD), FEA con FS ≥ 2, componentes COTS y cableado revisados; BOM de prototipo aprobado.

## 1. Checklist

| Ítem | Evidencia | Estado |
|---|---|---|
| Frame DS-I y DS-D en CAD paramétrico | `cad/openscad/{inspection,delivery}/`, ADR-011, ADR-012 | ✅ |
| Ensamble sin interferencias, holgura de hélices | `cad/exports/*/masas.json`: 0 interferencias, ≥ 33 mm (DS-I) y ≥ 48 mm (DS-D) | ✅ automático · 🟡 falta tu revisión en FreeCAD (S07-03, S08-03) |
| FEA | [fea_frames.md](../ingenieria/fea_frames.md): todos los casos OK. Las cargas ya incluyen FS 2.5 (vuelo) y 1.5 (aterrizaje accidental) | ✅ |
| Componentes COTS | [seleccion_cots.md](../ingenieria/seleccion_cots.md): evaluados con el modelo del S04 | ✅ con datos estimados a medir en el banco |
| Enlaces de radio | [radio_link_budget.md](../ingenieria/radio_link_budget.md): RC y telemetría con ≥ 30 dB de margen a 8 km | ✅ teórico · campo en el S14 |
| Cableado | [hardware/wiring.md](../../hardware/wiring.md): calibres, conectores, potencia, interferencias | ✅ |
| BOM del prototipo | [bom_prototipo_v1.md](../../manufacturing/bom/bom_prototipo_v1.md) + CSV con 2 proveedores por ítem | ✅ · 🟡 precios por cotizar |
| Plan de fabricación | [piezas_frame.md](../../manufacturing/procesos/piezas_frame.md), [dfm_dfa_ds-i.md](../ingenieria/dfm_dfa_ds-i.md) | ✅ |

## 2. El prototipo con componentes reales

| | DS-I | DS-D |
|---|---|---|
| Propulsión | T-Motor MN4006 KV380 + hélice 15" + ESC 4 en 1 con telemetría | MAD M6C12 EEE KV150 + 26" + APD 120F3 (telemetría para motor caído) |
| MTOW | 2.43 kg (S04: 2.69) | 15.07 kg con 5 kg (S04: 15.61) |
| Autonomía, batería nueva, 4,500 msnm | **32.1 min** (escenario D: ≥ 30) ✅ | **21.4 min** con 5 kg (escenario C: ≥ 20) ✅ |
| Empuje/peso a 5,000 msnm | 2.27 ✅ | 2.77 ✅ |
| Tope `MPC_THR_MAX` (protege la batería) | 0.91 | 0.86 |
| Costo por dron, prototipo | US$1,865 (2 baterías) | US$4,080 (2 baterías) |

## 3. Hallazgos

| # | Hallazgo | Consecuencia |
|---|---|---|
| 1 | **El prototipo cuesta ~2.5 veces lo presupuestado.** Motores de marca a precio unitario (3-4 veces el modelo del S04) y aviónica de desarrollo (~US$500 más por dron). | El precio objetivo del producto depende del motor y la electrónica propios (S17-S21) y del volumen. El costo de producción se recalcula en el S24. |
| 2 | **Varios datos del motor del DS-D son estimados** (Rm, I0, corriente máxima, precio). | Compra en dos fases: primero 2 motores al banco (S10), después la flota. |
| 3 | **La cámara SIYI A8 mini da 4.8 cm/px a 109 m.** Para 3 cm/px hay que volar a 67 m, con ~60 % más tiempo por hectárea. | Sirve para inspección y levantamientos de hasta ~35-40 ha por vuelo. Para la HU-01 completa (60 ha) falta una cámara de mapeo de 1" (decisión G2-3). |
| 4 | **A fondo, la batería se pasaría de su corriente** (DS-I 55 de 50 A; DS-D 262 de 225 A). | Se limita con `MPC_THR_MAX`; el empuje/peso sigue sobre 2.0. |
| 5 | La hélice del DS-I baja de 17" a 15"; el frame queda holgado. | Los brazos se pueden acortar ~25 mm en la v2 (menos masa). Por ahora no se toca: se valida primero en vuelo. |
| 6 | **El APD 80F3 está descontinuado y el 120F3 tiene stock irregular.** | Dos proveedores en el BOM; alternativa: cualquier ESC 12S con telemetría de corriente (BLHeli32/AM32 o CAN). |

## 4. Decisiones que debe tomar el equipo

| # | Pregunta | Recomendación |
|---|---|---|
| G2-1 | ¿Se aprueba la **compra de la fase A** (≈ US$3,800: baterías, cargadores, banco de empuje, 2 motores y 1 ESC de cada tipo, hélices)? | Sí: es lo de mayor plazo y valida los datos estimados antes de gastar en la flota |
| G2-2 | ¿Tamaño de la flota de prototipos? El plan dice 4 DS-I + 2 DS-D (≈ US$17,750 con repuestos y equipo; el plan suponía ≈ US$6,200) | Por etapas: **2 DS-I + 1 DS-D** para S11-S12 (≈ US$9,500 con equipo de tierra y repuestos) y completar a 6 para el enjambre de campo (S13-S15) |
| G2-3 | ¿Cámara del DS-I? | SIYI A8 mini para el prototipo; cámara de mapeo de 1" como accesorio a evaluar en el S13 |
| G2-4 | ¿RTK en los prototipos DS-I? (el escenario D lo deja opcional) | Sí en los prototipos: el levantamiento y el enjambre se validan con RTK |
| G2-5 | ¿Brazos desmontables del DS-D? (ADR-012, se aparta del plan) | Sí para la v1 |
| G2-6 | ¿Proveedores de piezas en Lima? | Cotizar con el texto de `piezas_frame.md` §4 (2 talleres por proceso) |

## Resultado
_(Completar en la revisión: Aprobado / Aprobado con observaciones / Rechazado, fecha y cambios pedidos. Luego tag git `cdr-v1.0`.)_
