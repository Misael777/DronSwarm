# Gate G1 · Revisión de diseño preliminar (PDR)

- Sprint: S06 · Tarea: S06-07
- Estado: **Pendiente de aprobación del equipo**. Recomendación: **aprobar con observaciones** (ver la sección 5).
- Fecha de preparación: 2026-10-18
- Depende del **Gate G0, que sigue abierto** (decisiones 1-14 en [G0_requisitos.md](G0_requisitos.md)). Si el G0 elige
  escenarios distintos de D / C / A, se regeneran la spec v1 y los modelos de simulación antes de cerrar este gate.

## Criterio del gate (plan)
Dimensionamiento cumple targets a 5,000 msnm; simulación de las historias de usuario y del enjambre satisfactoria
(< 10 % de desviación entre cálculo y simulación).

## 1. Checklist

| Ítem | Evidencia | Estado |
|---|---|---|
| Dimensionamiento a 5,000 msnm (empuje/peso ≥ 2.0) | [diseno_preliminar.md](../ingenieria/diseno_preliminar.md): DS-I 2.09, DS-D 2.12, DS-H 2.14 | ✅ |
| Autonomía | Escenarios D/C/A cumplen sus requisitos **propuestos**; los del PRD original no son alcanzables (G0 #8-10) | 🟡 depende del G0 |
| Modelo validado contra drones reales | M4E calibrado; M400 con −13.4 % (criterio < 10 %: no cumple, el error es conservador) | 🟡 observación |
| Cálculo ↔ simulación < 10 % | rpm en vuelo vs cálculo: DS-I +1.6 %, DS-D −0.1 %, DS-H 0.0 % ([spec_v1.md §3](../ingenieria/spec_v1.md)) | ✅ (coherencia, no validación independiente) |
| Spec v1 (masa, empuje, energía) | [spec_v1.md](../ingenieria/spec_v1.md) | ✅ propuesta |
| Enjambre: formación, comunicaciones, evitación | 1,600 corridas Monte Carlo y 20 en PX4 + Gazebo, todas sin colisiones ([evidencia](../evidencias/simulacion/README.md)) | ✅ |
| Fallas y failsafes (HU-09) y geocerca (HU-10) | [evidencia](../evidencias/simulacion/README.md): 6 de 7 casos con aterrizaje seguro tras los ajustes; GNSS no | 🟡 2 requisitos de hardware nuevos |
| Historias de usuario simuladas | Matriz historia → prueba → criterio en [evidencias/simulacion](../evidencias/simulacion/README.md) | 🟡 HU-03/04/05/11 pendientes (S13) |
| Arquitectura del enjambre | [ADR-010](../decisiones.md) | propuesta |

## 2. Resultados principales

**Dimensionamiento (S04).** Los tres drones cumplen empuje/peso ≥ 2.0 a 5,000 msnm con hover entre 43 y 44 % del empuje
máximo. Autonomía con batería nueva a 4,500 msnm y 0 °C: DS-I 31.3 min, DS-D 20.3 min con 5 kg, DS-H 16.4 min con 10 kg.

**Cálculo ↔ simulación (S06-05).** Los vuelos en PX4 + Gazebo giran los motores a las rpm que predijo el cálculo
(diferencia ≤ 1.6 %). Eso confirma que el modelo de simulación representa al diseño; no reemplaza al banco de empuje (S10).

**Enjambre (S06-01/02/03).** Consenso distribuido + evitación + radio simulada:
- Simulador rápido: 1,600 corridas con evitación en 8 condiciones (nominal, 30 % y 50 % de pérdida de paquetes, viento
  de 8 m/s, Wi-Fi, caída de radio en tránsito y en el cruce, líder-seguidor): **0 colisiones**. Sin evitación, el mismo
  escenario choca en el 100 % de las corridas.
- PX4 + Gazebo: **20 de 20 corridas completas y 0 colisiones** (14 nominales, 3 con 30 % de pérdida, 3 con un dron sin
  radio); separación mínima 2.23 m, torre a 3.11 m libres, simulación en tiempo real (RTF 0.98). Criterio del plan cumplido.
  Seis corridas se repitieron porque un dron no despegó en el arranque (entorno de simulación, no el control).
- HU-08 (levantamiento por sectores): 6 drones en capas de 30-80 m, separación mínima 3D 11.88 m (criterio ≥ 10 m),
  "abortar todo" deja a los 6 en casa en 103 s.

**Fallas (S06-04), en PX4 + Gazebo, juzgadas con la posición real:**

| Falla | Resultado | Estado |
|---|---|---|
| Motor caído DS-D (ESC con telemetría) | PX4 lo detecta en 60 ms, lo retira y aterriza solo en el lugar: 0.77 m/s, 11° de inclinación máx. | ✅ |
| Motor caído DS-H (8 motores) | ídem, aterrizaje autónomo a 0.74 m/s | ✅ |
| Motor caído DS-D **sin** telemetría de ESC | PX4 sigue contando con el motor muerto: cae 20 m en 10 s | ❌ → requisito de hardware |
| Batería crítica | RTL automático, aterriza a 0.1 m de casa | ✅ (con umbrales mineros, ver hallazgo 8) |
| Pérdida de enlace con la estación | RTL automático, aterriza a 0.1 m de casa | ✅ |
| Geocerca (HU-10) | misión que la cruza: rechazada; orden de salir: ignorada (no se movió más de 0.3 m) | ✅ · la reacción ante una violación en vuelo no se ejercitó |
| Pérdida de GNSS | aterriza sin posición: el viento de 4 m/s lo arrastra 60 m y se vuelca al tocar suelo | ❌ → requisito de hardware |

## 3. Hallazgos que cambian requisitos o diseño

| # | Hallazgo | Consecuencia / acción |
|---|---|---|
| 1 | **Motor caído (DS-D):** sin detección, PX4 sigue contando con el motor muerto y el dron cae (20 m en 10 s, llega al suelo a 12 m/s). Con detección pero sin airmode, la asignación sacrifica el empuje para buscar cabeceo y también cae. | Requisito nuevo: **ESC con telemetría de corriente** (DShot/BLHeli32/AM32) y `CA_FAILURE_MODE = 1`, `COM_ACT_FAIL_ACT = 2`, `MC_AIRMODE = 1` (ya en los airframes de 6 y 8 motores). Ensayo en banco y vuelo atado en S10-S12. En SITL hizo falta un parche de PX4 (`simulation/px4/patches/`). |
| 2 | **Pérdida de radio entre drones:** sin protocolo, chocaba en 17-20 de cada 20 corridas. | Protocolo adoptado (ADR-010): frenar y subir 8 m a los 0.8 s; los demás esquivan la última posición. Ahora: 0 en 400 corridas. |
| 3 | **Cruce de muchos drones:** la evitación reactiva sin sesgo chocaba en ~3 % de las corridas. | Sesgo a la derecha en todo conflicto (rotonda espontánea). Ahora: 0 en 1,600. |
| 4 | **Viento de 8 m/s:** la distancia libre a obstáculos bajó a ~1 m (sin contacto). | Con viento fuerte: margen de obstáculos 4 m y crucero más lento. Ensayo en campo (S14). |
| 5 | **HU-08 vs formación cerrada:** la historia pide ≥ 10 m entre drones; la formación cerrada vuela a 3-6 m. | Formación cerrada solo para tránsito con evitación; las misiones de trabajo usan sectores y capas (≥ 10 m). Confirmar con el usuario minero (S02-07). |
| 6 | **Líder-seguidor:** error de formación ~70 % mayor y punto único de falla. | Consenso como arquitectura principal (ADR-010). |
| 7 | Parámetros de evitación dimensionados para DS-I. | Márgenes por tamaño de dron para enjambres mixtos (v2). |
| 8 | **Batería:** el estimador de PX4 lee el 6 % del simulador como ~19 %; con el umbral crítico por defecto (7 %) nunca vuelve. | Umbrales por misión (aviso 35 %, RTL 25 %, aterrizaje 10 %) y estimación por energía/tiempo de regreso; calibrar con la batería real (S10). |
| 9 | **Pérdida de GNSS:** sin posición, PX4 aterriza a ciegas, el viento lo arrastra y se vuelca. En un tajo el GNSS se degrada por las paredes. | Requisito nuevo: **flujo óptico + telémetro** para sostener la posición sin GNSS (selección COTS, S08); ensayo en el tajo (S14). |

## 4. Riesgos abiertos

- **Modelo vs drones reales −13 %** (conservador): el banco de empuje (S10) puede achicar el DS-D.
- **Radio real:** el modelo usa hojas de datos; la latencia y la pérdida reales en un tajo (paredes de 60 m) se miden en el S14.
- **Simulación ≠ campo:** cámara, GNSS con multitrayecto en el tajo y polvo no están modelados.
- **Gate G0 abierto:** sin las decisiones de requisitos, esta revisión aprueba un diseño sobre requisitos propuestos.

## 5. Decisiones que debe tomar el equipo

| # | Pregunta | Recomendación |
|---|---|---|
| G1-1 | ¿Se aprueba la spec v1 (escenarios D/C/A) como base del diseño mecánico (S07-S09)? | Sí, condicionado al G0 #8-13 |
| G1-2 | ¿ESC con telemetría de corriente como requisito de DS-D y DS-H? | Sí: sin eso el motor caído no es recuperable |
| G1-3 | ¿Se aprueba ADR-010 (consenso + evitación + protocolo de pérdida de radio)? | Sí |
| G1-4 | ¿Separación de trabajo ≥ 10 m (HU-08) y formación cerrada solo en tránsito? | Sí; validar con el usuario minero |
| G1-5 | ¿Se acepta el −13 % del modelo frente al M400 hasta el banco de empuje (S10)? | Sí, porque es conservador |
| G1-6 | ¿Flujo óptico + telémetro como requisito (pérdida de GNSS en el tajo)? | Sí: ≈ US$30-120 por dron; evita deriva y vuelco |

## Resultado
_(Completar en la revisión: Aprobado / Aprobado con observaciones / Rechazado, fecha y cambios pedidos. Luego tag git `pdr-v1.0`.)_
