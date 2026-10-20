# Motor propio DronSwarm · plan del subproyecto

> Estado: **aprobado** (2026-10-20). Adelanto aceptado en ADR-013 (`docs/decisiones.md`).
> Reemplaza y adelanta el alcance de los sprints S17-S19 del plan general.

## 1. Objetivo

Diseñar, simular, fabricar y probar **nuestro propio motor brushless** para el DS-I y el DS-D, **más eficiente
que el comercial** en el punto que más importa (hover a 4,500-5,000 msnm). Se evalúa también un **reductor**
(cicloidal, armónico, planetario u otro). La fabricación es en casa: impresora 3D y cortadora láser para las
láminas de acero. Solo se compran los materiales.

Entregables visibles para el usuario:
1. Cálculos y simulaciones reproducibles (Python, en esta carpeta).
2. Una **lista de compras de materiales** en Excel, con el mismo formato que la del prototipo.
3. Una **página HTML didáctica** que explica cada parte del motor (qué es, para qué sirve, de qué se hace y cómo se fabrica aquí).
4. Archivos listos para fabricar: DXF para el láser y STL para la impresora.

## 2. Qué tiene que cumplir (puntos de operación)

Los valores salen de `engineering/` (dimensionamiento y selección del S09). Son aproximados y la fase M1 los recalcula
con la hélice real y el aire de 5,000 msnm.

| | DS-I (hélice 15-17") | DS-D (hélice 26") |
|---|---|---|
| Motor comercial a superar | T-Motor MN4006 KV380 · 68 g · US$75 | MAD M6C12 KV150 · 257 g · US$170 |
| Hover por motor (potencia en el eje) | ~70 W · **0.21 N·m a ~3,100 rpm** | ~310 W · **1.12 N·m a ~2,600 rpm** |
| Máximo por motor (empuje/peso ≈ 2.3) | ~0.48 N·m a ~4,700 rpm (~240 W) | ~2.6 N·m a ~4,000 rpm (~1.1 kW) |
| Batería | 6S (22.2 V nominal) | 12S (44.4 V nominal) |
| Eficiencia del comercial en hover | 84-85 % | 86 % |
| Montaje | DMI-S: 4×M3 en Ø19/Ø25 | DMI-L: 4×M4 en Ø35 |

**Criterios de éxito (Gate G5, adelantado):**

| Criterio | Meta |
|---|---|
| Eficiencia en hover (motor, o motor + reductor) | ≥ 88 % (el comercial da 84-86 %) |
| Masa | ≤ la del comercial + 10 %. Con reductor cuenta el conjunto. |
| Temperatura del bobinado a potencia máxima continua, 5,000 msnm, 20 °C de ambiente | < 120 °C |
| Costo de materiales por motor | ≤ 30 % del comercial: DS-I ≤ US$22, DS-D ≤ US$50 |
| Respuesta de empuje | Constante de tiempo ≤ la del comercial, para no degradar el control de actitud |
| Compatibilidad | Funciona con los ESC actuales (BLHeli32/AM32), dentro de su límite de eRPM |

## 3. Arquitectura: motor directo o con reductor

La pregunta central es si conviene un motor lento que mueva la hélice directo, o un motor rápido y chico con un reductor.

### Lo que dice la física (hipótesis que la fase M3 tiene que confirmar o descartar)

- **Las hélices grandes ya giran lento** (2,600-3,100 rpm en hover). Por eso los multirrotores usan outrunners
  de directo: el motor ya trabaja cerca de su punto óptimo, sin pérdidas de engranaje.
- **El reductor gana en masa y pierde en eficiencia.** Un motor de 15,000 rpm con reducción 5:1 pesa bastante
  menos para el mismo torque, pero cada etapa se come energía:

| Reductor | Eficiencia típica | Ventaja | Problema en un dron |
|---|---|---|---|
| Planetario (1 etapa) | 95-97 % | El más eficiente de los reductores; compacto y coaxial | Ruido y desgaste; engranajes impresos no aguantan 1 kW continuo |
| Cicloidal | 85-93 % | Mucho torque en poco espacio; casi sin juego | Disco excéntrico que vibra a alta velocidad (hacen falta 2 discos a 180°) y rodamientos cargados |
| Armónico (strain wave) | 70-85 % | Reducción alta en una sola etapa | El flexspline se fatiga girando continuo a miles de rpm; pierde mucho a alta velocidad. Es para robots, no para hélices |
| Correa dentada (HTD/GT2) | 95-98 % | Barata, silenciosa, se imprime | No es coaxial: obliga a cambiar el brazo |
| Directo (sin reductor) | — (100 %) | Sin pérdidas, sin juego, respuesta rápida | Motor más grande y pesado para el mismo torque |

- **El reductor también afecta el control.** La inercia del motor se refleja en la hélice multiplicada por N²
  (N = relación de reducción) y el juego mete retardo. Esto se simula en la fase M3 con el modelo de actitud de PX4.
- **Expectativa honesta:** para **la máxima eficiencia** casi seguro gana el **directo**. El reductor solo se
  justifica si en el **DS-D** (o un futuro DS-H con hélices > 30") el ahorro de masa le gana a la pérdida de
  eficiencia en autonomía. La fase M3 lo decide con números (autonomía del dron completo), no con intuición.

### Topología base del motor

- **Outrunner de flujo radial**, con el rotor por fuera.
  - DS-I: 12 ranuras y 14 polos (12N14P).
  - DS-D: 24N28P o 36N42P.
  - La fase M2 compara bobinados concentrados de doble capa.
- **Imanes de arco o segmentados N52H, comprados**, pegados a un **yugo de rotor de láminas de acero cortadas con láser**.
  También se evalúa un **arreglo Halbach**, que da más torque por gramo y necesita menos yugo, pero tiene más piezas.
- **Estator de láminas de acero eléctrico (silicio) de 0.2-0.35 mm, cortadas con láser**, apiladas y pegadas.
  - No sirve acero común: las pérdidas en el hierro se disparan.
  - El corte con láser degrada el borde, y la fase M2 lo modela como una pérdida extra.
- **Cobre esmaltado clase H** (200 °C) y bobinado a mano con un útil impreso.
- **Piezas impresas** (campana, base y soportes) en PA12-CF o PC, alejadas del calor. El eje y los rodamientos se compran.

## 4. Estructura de la carpeta

```text
motor/
├── PLAN.md                  # este documento
├── README.md                # cómo correr todo
├── requisitos/              # puntos de operación (JSON generado desde engineering/) y fichas de los comerciales
├── informes/                # informes generados por fase (M1_referencia_cots.md, …)
├── calculo/                 # Python: dimensionamiento analítico, bobinado, pérdidas, térmico, optimizador
├── fem/                     # simulación electromagnética 2D (modelos, mallas, resultados)
├── reductores/              # modelos y comparación: directo / planetario / cicloidal / armónico / correa
├── fabricacion/             # proceso: corte láser, impresión, bobinado, pegado de imanes, balanceo
├── pruebas/                 # plan y resultados en el banco de empuje (tools/bench, S10)
├── bom/                     # lista de compras de materiales (CSV + Excel)
├── docs/partes.html         # guía didáctica de cada parte del motor
└── tests/                   # pruebas unitarias de los cálculos
```

El CAD sigue la regla del repo: la fuente va en `cad/openscad/motor/` y los DXF y STL en `cad/exports/motor/`,
y `motor/fabricacion/` los referencia.

## 5. Fases

Cada fase termina con algo verificable. Las horas son estimadas.

### M0 · Base y requisitos (4 h)
- Generar `requisitos/puntos_operacion.json` desde `engineering/` (hover, máximo, crucero, 4,500 y 5,000 msnm, aire frío y caliente).
- Fichas de materiales: acero eléctrico (curva B-H y pérdidas), imanes N52H (Br y Hcj según temperatura), cobre y plásticos de impresión.
- **Hecho cuando:** los puntos de operación coinciden con el dimensionamiento con un error < 2 %.

### M1 · Modelo del motor comercial (referencia) (6 h)
- Modelar el MN4006 y el M6C12 con el mismo código que se usará para el propio, a partir de sus datos (Kv, Rm, I0, masa, medidas).
- Si ya hay datos del banco (S10), calibrar contra ellos.
- **Hecho cuando:** el modelo reproduce la eficiencia del comercial en hover con un error ≤ 2 puntos. Sin esto no se puede decir que el propio es mejor.

### M2 · Dimensionamiento analítico y optimización del motor directo (16 h)
- `calculo/`:
  - geometría (diámetro del entrehierro, largo del paquete, ranuras y polos);
  - bobinado (factor de bobinado, vueltas por diente, conexión estrella o triángulo);
  - Kv, resistencia y relleno de ranura;
  - pérdidas en cobre (con efecto pelicular), en hierro (Steinmetz, más el borde cortado con láser), por fricción y por remolinos en los imanes;
  - masa y costo de materiales.
- Optimizador multiobjetivo: eficiencia en hover, masa y costo, con las restricciones de temperatura, eRPM del ESC y tamaño del montaje DMI.
- **Hecho cuando:** hay un frente de Pareto y 2-3 diseños candidatos por dron que en el cálculo cumplen la tabla del §2.

### M3 · Estudio de reductores (12 h)
- `reductores/`: un modelo de eficiencia, masa e inercia reflejada para cada tipo del §3, y para cada uno el motor rápido óptimo (repitiendo M2 a otra velocidad).
- Evaluación a nivel dron: autonomía con `engineering/` (masa + eficiencia) y respuesta de actitud (constante de tiempo y juego).
- Si un reductor entra en la decisión: un prototipo impreso rápido del cicloidal y del planetario para medir eficiencia en el banco.
- **Hecho cuando:** hay un informe con una tabla "directo vs reductores" en autonomía, masa, eficiencia, costo y riesgo, y una recomendación (ADR).

### M4 · Simulación electromagnética 2D (FEM) (16 h)
- Validar los candidatos de M2/M3: distribución de flujo, saturación, torque de *cogging*, contra-FEM (forma de onda y Kv), torque contra corriente y pérdidas en el hierro.
- Herramienta (se decide en un spike de 2 h):
  - **gmsh + GetDP**: nativo de Linux, entra en CI, se usa gmsh ya instalado.
  - **FEMM 4.2 en Windows**, llamado desde WSL: estándar de la industria, sirve para comparar.
  - Se usa una y la otra verifica un caso.
- Desmagnetización de los imanes en el peor caso: corriente máxima a 120 °C.
- **Hecho cuando:** el FEM y el cálculo analítico coinciden en Kv y torque dentro de un 5 %, y se cumplen el cogging y la desmagnetización.

### M5 · Térmico y mecánico (10 h)
- Red térmica (bobinado → estator → aire) con la convección del flujo de la hélice a densidad de 5,000 msnm.
- Mecánica:
  - velocidad crítica del rotor;
  - esfuerzo en el pegado de imanes por fuerza centrífuga a la velocidad máxima + 20 %;
  - rodamientos (vida L10);
  - piezas impresas por debajo de su temperatura de ablandamiento.
- Reutiliza el flujo de FEA del S07 (gmsh + CalculiX).
- **Hecho cuando:** el bobinado queda < 120 °C y todas las piezas tienen factor de seguridad ≥ 2.

### M6 · CAD, archivos de fabricación y lista de compras (14 h)
- OpenSCAD paramétrico desde el diseño elegido: lámina del estator y anillo del yugo (DXF para el láser), campana, base y útiles en STL, y el ensamble para FreeCAD.
- Útiles:
  - jig de bobinado;
  - plantilla para pegar los imanes con el paso correcto;
  - prensa para apilar las láminas;
  - soporte de balanceo.
- `bom/`: materiales por motor y para un lote de 12 (+ repuestos, como en el S18-06), con precio, proveedor y plazo. Solo material: el corte y la impresión son en casa.
- **Hecho cuando:** los DXF y STL se regeneran con un comando y el Excel de compras sale con totales verificados.

### M7 · Guía didáctica HTML (6 h)
- `docs/partes.html`: una página interactiva con el corte del motor por capas. Para cada parte explica:
  - qué es;
  - qué hace;
  - de qué material;
  - por qué esa forma;
  - cómo se fabrica aquí;
  - errores típicos.
- Partes: estator y láminas, bobinado, imanes, yugo, campana, eje, rodamientos, base, sensores y el reductor si se elige.
- Incluye animaciones simples del campo giratorio y de la conmutación, y el paso a paso de armado.
- **Hecho cuando:** se entiende sin saber de motores (lo revisas tú).

### M8 · Prototipos y pruebas (24 h + tiempos de compra)
- Fabricar 2 motores del primer dron y luego el lote:
  - cortar y apilar las láminas;
  - bobinar;
  - pegar los imanes;
  - ensamblar;
  - balancear.
- Banco (S10): Kv, Rm, I0, empuje contra acelerador, g/W, temperatura, vibración y 10 h de durabilidad.
- Vuelo en un DS-I o DS-D comparado con el comercial: autonomía y temperaturas.
- **Gate G5:** se fabrica si cumple el §2; si no, se sigue con el comercial y se documenta por qué.

**Total estimado: ~110 h de trabajo**, más los plazos de compra (imanes y acero eléctrico: 2-4 semanas).

## 6. Orden propuesto

1. **DS-I primero.** Es el motor chico: materiales baratos, iteración rápida y se prueba en el banco que ya existe.
   Sirve para aprender el proceso (corte de láminas, bobinado, pegado de imanes) sin arriesgar mucho dinero.
2. **DS-D después**, con el mismo código y el proceso ya probado. Es donde está el ahorro grande (US$1,020 por dron
   en motores), y es el único caso donde el reductor puede tener sentido.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| La cortadora láser no corta bien acero eléctrico delgado (un láser de CO₂ no corta acero; hace falta de fibra) | Confirmar el tipo y la potencia del láser (pregunta abierta). Plan B: comprar las láminas cortadas o un estator laminado listo y hacer en casa lo demás |
| El corte degrada el acero en los bordes, lo que significa más pérdida en el hierro | Modelarlo en M2; probar un recocido; dientes no demasiado angostos |
| Imanes N52H: plazo, precio y manipulación peligrosa (se golpean, se rompen, pellizcan) | Pedir temprano, usar la plantilla de pegado y escribir un procedimiento de seguridad |
| Piezas impresas cerca del bobinado caliente | Las partes calientes van en metal o en PA-CF/PC; el térmico de M5 lo verifica |
| Desbalance del rotor, que trae vibración y ruido en las fotos | Soporte de balanceo y criterio de vibración del S11 |
| El reductor degrada el control de actitud | Simulación en M3 antes de construir |
| El motor propio no supera al comercial | Es un resultado válido: el Gate G5 lo documenta y se sigue con el comercial |

## 8. Preguntas abiertas para el usuario

1. **Cortadora láser:** ¿es de fibra o de CO₂? ¿Qué potencia y qué espesor máximo de acero corta?
2. **Impresora 3D:** ¿con qué materiales imprime (PLA, PETG, ABS/ASA, PA-CF, PC)? ¿Tiene cámara cerrada y boquilla endurecida?
3. **Prioridad:** ¿empezamos por el DS-I (recomendado: aprender barato) o directo por el DS-D (donde está el ahorro)?
