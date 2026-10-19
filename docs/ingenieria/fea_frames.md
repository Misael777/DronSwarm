# FEA de los frames · DS-I y DS-D

> Generado por `tools/fea/fea_report.py` el 2026-10-19 desde `cad/freecad/<grupo>/fea/resultados.json`. Para recalcular: `.venv/bin/python tools/fea/run_fea.py inspection|delivery`.

## Método

- **Sólidos:** STEP del CAD, mallado con gmsh en tetraedros cuadráticos (C3D10) de ~1.6 mm y resuelto con CalculiX 2.22 (ambos incluidos en FreeCAD 1.0). Los apoyos y las cargas se eligen por geometría: superficie del agujero del tubo, caras contra las placas, etc.
- **Brazos:** viga tubular (elementos B32R, sección PIPE) con la masa del motor, el soporte y la hélice en la punta. El análisis modal se verificó contra la fórmula analítica: 82.2 Hz contra 82.1 Hz.
- **Cargas de vuelo:** empuje máximo a 5,000 msnm escalado a nivel del mar por la densidad del aire (×1.88, cota superior) y multiplicado por FS 2.5. **Cargas de aterrizaje** (accidentales) × FS 1.5. Como las cargas ya incluyen el factor, el criterio es FS calculado ≥ 1.
- **Esfuerzo informado:** percentil 99.5 de von Mises. El pico absoluto aparece en las esquinas de los apoyos (singularidad numérica) y se reporta aparte.
- **Piezas impresas (PA12-CF):** se comparan contra 50 MPa, la resistencia en el plano de las capas. Entre capas es ~50 %, por eso las piezas se orientan en la impresora según la carga (`dfm_dfa_ds-i.md` y `manufacturing/procesos/piezas_frame.md`).

## DS-I

Empuje máximo por motor a nivel del mar: 25.9 N → carga de diseño 64.9 N.

| Caso | Carga de diseño | Resultado | FS | Estado |
|---|---|---|---|---|
| Soporte de motor DMI-S (PA12-CF) | empuje 65 N sobre la placa DMI | von Mises 1.4 MPa (p99.5; pico 3.0), desplazamiento máx. 0.038 mm, 25,468 elementos | 36.15 (sobre 50 MPa) | ✅ |
| Bloque de brazo (arm_block, PA12-CF) | momento del brazo 16.5 N·m y corte 65 N | von Mises 4.4 MPa (p99.5; pico 11.2), desplazamiento máx. 0.009 mm, 29,906 elementos | 11.25 (sobre 50 MPa) | ✅ |
| Abrazadera de pata (PA12-CF) | caída de 1 m en 2 patas: 891 N por pata × 1.5 (+30 % lateral), carrera 30 mm | von Mises 13.7 MPa (p99.5; pico 22.7), desplazamiento máx. 0.115 mm, 16,914 elementos | 3.64 (sobre 50 MPa) | ✅ |
| Tubo del brazo en vuelo (analítico) | 65 N en la punta, 255 mm | σ = 61.2 MPa | 8.16 (mín. 1.0) | ✅ |
| Tubo del brazo en la caída (analítico) | 891 N a 70 mm del bloque | σ = 230.8 MPa | 2.17 (mín. 1.5) | ✅ |
| Modal del brazo (viga B32R + masa en la punta) | motor + soporte + hélice = 0.123 kg en la punta, 263.0 mm | 1.er modo 78.3 Hz; 1P = 52.1 Hz, 2P = 104.2 Hz; separación 25 % (entre 1P y 2P) | — | ✅ |

## DS-D

Empuje máximo por motor a nivel del mar: 101.5 N → carga de diseño 253.7 N.

| Caso | Carga de diseño | Resultado | FS | Estado |
|---|---|---|---|---|
| Soporte de motor DMI-L (PA12-CF) | empuje 254 N sobre la placa DMI | von Mises 3.4 MPa (p99.5; pico 12.8), desplazamiento máx. 0.134 mm, 47,839 elementos | 14.9 (sobre 50 MPa) | ✅ |
| Bloque de brazo (arm_socket, PA12-CF) | momento del brazo 139.0 N·m y corte 254 N | von Mises 19.0 MPa (p99.5; pico 171.2), desplazamiento máx. 0.048 mm, 61,771 elementos | 2.63 (sobre 50 MPa) | ✅ |
| Soporte de pata (PA12-CF) | aterrizaje a 2 m/s con carga en 2 patas: 1041 N por pata × 1.5 (+30 % lateral) | von Mises 13.9 MPa (p99.5; pico 26.9), desplazamiento máx. 0.107 mm, 25,037 elementos | 3.6 (sobre 50 MPa) | ✅ |
| Gancho de carga (aluminio 6061-T6) | caja de 5 kg × 2 (tirón) × 2.5 = 245 N en la anilla | von Mises 25.0 MPa (p99.5; pico 37.4), desplazamiento máx. 0.025 mm, 38,746 elementos | 9.6 (sobre 240 MPa) | ✅ |
| Cuerpo de liberación (PA12-CF) | 245 N en el perno del gancho | von Mises 2.7 MPa (p99.5; pico 8.6), desplazamiento máx. 0.087 mm, 125,467 elementos | 18.21 (sobre 50 MPa) | ✅ |
| Tubo del brazo en vuelo (analítico) | 254 N en la punta, 548 mm | σ = 299.6 MPa | 1.67 (mín. 1.0) | ✅ |
| Modal del brazo (viga B32R + masa en la punta) | motor + soporte + hélice = 0.456 kg en la punta, 555.9 mm | 1.er modo 18.3 Hz; 1P = 43.8 Hz, 2P = 87.6 Hz; separación 58 % (primer modo bajo 1P: se cruza solo al acelerar los motores desde reposo) | — | ✅ |

## Hallazgos de diseño

- **Tren del DS-I:** con un pie macizo de TPU 95A el tren queda casi rígido (≈ 750 N/mm) y una caída de 1 m daría ≈ 4.5 kN por pata. Se rediseñó como pie amortiguador de TPU 85A con giroide al 15 % (≈ 30 N/mm, 30 mm de carrera): ≈ 0.9 kN por pata. Las patas se alargaron para que la cámara no toque el suelo con el pie comprimido.
- **Soportes de motor del DS-I:** FS ≈ 36, sobredimensionados. Se acortó el manguito (34 → 26 mm) por masa. La forma la manda la rigidez y la impresión, no la resistencia.
- **DS-D:** la bisagra plegable de aluminio del primer diseño pesaba 250 g por brazo. Con brazos desmontables (ADR-012), el bloque impreso resiste el momento del brazo con FS 2.6.
- **Bloque de brazo del DS-D:** el percentil 99.5 da FS 2.6, pero el pico local llega a ~170 MPa en el borde de la boca, donde la carga del tubo entra concentrada en la malla (singularidad de contacto). En la pieza real el tubo aplasta un poco el PA12 y reparte la carga. Si el prototipo muestra desgaste u ovalización en la boca, la solución es un buje de aluminio de 1 mm (≈ 8 g por brazo).
- **Modo del brazo del DS-D:** 18 Hz, bajo 1P (44 Hz) con 58 % de separación. Es normal en drones grandes: se cruza solo al arrancar los motores. Se verifica con el acelerómetro en el banco (S10).
- **Pendiente:** el FEA no reemplaza los ensayos. En el S10 vienen el banco de empuje, la carga estática del gancho a 2.5 × 5 kg y la caída de 1 m del DS-I con piezas impresas reales, porque la resistencia del PA12-CF depende del perfil de impresión.
