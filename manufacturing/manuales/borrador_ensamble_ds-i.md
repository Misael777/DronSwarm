# Manual de ensamble del DS-I · BORRADOR (S11-01)

> Borrador escrito antes del primer armado. Al armar el DS-I #1, **cronometra cada paso y anota dificultades y
> mejoras** en las columnas vacías. Ese registro es la base del manual definitivo (S23).

- Piezas y tornillería: [dfm_dfa_ds-i.md](../../docs/ingenieria/dfm_dfa_ds-i.md) · Cableado: [wiring.md](../../hardware/wiring.md)
- Ensamble 3D para consultar: `cad/freecad/inspection/ds-i_ensamble_generado.FCStd` (o `cad/exports/inspection/ds-i_ensamble.png`)
- Herramientas: llave allen de 2.5 mm, llave de 5.5 mm, soldador de 60 W o más, pinza, multímetro, fijador de rosca azul, termocontraíble.

## Pasos

| # | Paso | Detalle | Tiempo objetivo | Tiempo real | Dificultades / mejoras |
|---|---|---|---|---|---|
| 1 | Inspección de piezas | Contra `hardware/prototipos/frames/README.md`: masas y ajuste del tubo en un bloque | 5 min | | |
| 2 | Bloques sobre la placa inferior | 16 × M3×35 desde abajo, sin apretar; la placa con el **agujero de 16 mm adelante** | 5 min | | |
| 3 | Tubos de brazo | Insertar hasta el tope interior del bloque; la línea de 287 mm queda hacia afuera | 3 min | | |
| 4 | Placa superior | Encima de los bloques. Apretar en cruz las 16 tuercas (1.2 N·m) y luego el tornillo de apriete de cada bloque | 5 min | | |
| 5 | Patas | Abrazaderas a 70 mm del bloque, con la oreja hacia afuera; tubos Ø12 y pasador M3; pies de TPU a presión | 6 min | | |
| 6 | Soportes y motores | Soporte en la punta, apretar en el tubo con la placa DMI **horizontal** (nivel); motor con sus 4 tornillos y fijador de rosca. Los cables pasan por el agujero del soporte hacia dentro del tubo | 8 min | | |
| 7 | ESC 4 en 1 y controladora | Pila sobre la placa superior: ESC abajo, controladora arriba sobre ojales de goma, con la **flecha hacia adelante** | 10 min | | |
| 8 | Motores al ESC | Cortar los cables de motor a medida, soldar al ESC 4 en 1 (orden según QGC); termocontraíble | 15 min | | |
| 9 | Potencia | Módulo PM02 → XT90-S de la batería, cable de 12 AWG trenzado. BEC de 5 V para la Pi | 10 min | | |
| 10 | Computadora y radios | Raspberry Pi 5 en su soporte, RFD900x, ESP32, receptor ExpressLRS; cables JST-GH a la controladora (TELEM1 RFD, TELEM2 Pi, TELEM3 telemetría de ESC) | 15 min | | |
| 11 | GNSS y flujo óptico | Mástil de 15 cm para el F9P (flecha adelante); MTF-01P bajo la placa inferior, mirando abajo, sin obstrucción | 8 min | | |
| 12 | Cámara | Placa superior del adaptador, 4 amortiguadores, placa inferior y SIYI A8 mini; cable Ethernet a la Pi y UART a la controladora | 10 min | | |
| 13 | Bandeja y batería | Bandeja con 4 × M3×10; correas por las ranuras | 3 min | | |
| 14 | Carcasa IP54 | Junta EPDM en el canal (sin estirar); prensaestopa M12 con todos los cables; 8 × M3×10 con arandela de nylon, en cruz | 8 min | | |
| 15 | Control | Peso total en balanza (objetivo: 2.43 kg ± 5 %) y centro de gravedad (colgar de un hilo: dentro de ± 10 mm del eje) | 5 min | | |
| | **Total** | | **≈ 2 h** (primera vez) · objetivo de serie: 45 min | | |

## Antes de energizar

- Continuidad: sin cortocircuito entre + y − del XT90 (multímetro). Primera conexión con **limitador de humo**
  (fusible de 5 A o lámpara en serie).
- Sin hélices hasta completar `hardware/calibration.md`.
EOF
cat > manufacturing/manuales/borrador_ensamble_ds-d.md <<'EOF'
# Manual de ensamble del DS-D · BORRADOR (S12-01)

> Igual que el del DS-I: **cronometra y anota** al armar el DS-D #1. Diferencias principales: brazos desmontables con
> levas (ADR-012), 12S con barra de cobre, mecanismo de liberación de carga y tren de esquíes.

- Piezas: `cad/exports/delivery/masas.json` · Proceso: [piezas_frame.md](../procesos/piezas_frame.md) · Cableado: [wiring.md](../../hardware/wiring.md)
- Herramientas: las del DS-I más una llave allen de 3 mm, un soldador de 100 W para 6 AWG y una crimpadora para AS150U y XT60.

| # | Paso | Detalle | Tiempo objetivo | Tiempo real | Dificultades / mejoras |
|---|---|---|---|---|---|
| 1 | Inspección | Masas y ajuste del tubo Ø22 en un bloque desmontable (entra a mano, sin juego) | 10 min | | |
| 2 | Bloques desmontables | 6 bloques sobre la placa inferior, 6 × M4 cada uno, sin apretar; conector XT60 hembra en su alojamiento | 15 min | | |
| 3 | Barra de cobre y ESC | Barra de distribución al centro entre placas; 6 ESC APD en los espacios entre bloques; cables de 12 AWG del ESC al XT60 del bloque | 40 min | | |
| 4 | Placa superior | Apretar en cruz los 36 × M4 (2.5 N·m) | 10 min | | |
| 5 | Brazos | Por brazo: soporte DMI-L + motor en la punta (fijador de rosca), luz anticolisión a 90 mm, cables por el tubo hasta un XT60 macho; insertar en el bloque y cerrar las 2 levas | 6 × 8 min | | |
| 6 | Tren de esquíes | 4 soportes bajo la placa (4 × M4), patas Ø16 con pasador, T del esquí, esquíes y zapatas de TPU | 20 min | | |
| 7 | Mecanismo de liberación | Cuerpo al centro bajo la placa (4 × M4); gancho con perno M5 y arandelas; pasador de traba, resorte, servo y micro-interruptor. **Prueba:** sin energía, el gancho sostiene 10 kg y no abre | 25 min | | |
| 8 | Aviónica | Como el DS-I (pasos 7, 10 y 11) más reguladores de 12, 7.4 y 5 V; cámara FPV adelante | 40 min | | |
| 9 | Batería y carcasa | Bandeja arriba-atrás con correas de leva; carcasa IP54 adelante con prensaestopa M16 | 15 min | | |
| 10 | Control | Peso (objetivo: 10.07 kg sin carga ± 5 %; 15.07 kg con la caja de 5 kg) y centro de gravedad con la caja colgada | 10 min | | |
| | **Total** | | **≈ 4.5 h** la primera vez | | |

## Montaje y desmontaje en campo (brazos)

Abrir las 2 levas, desconectar el XT60 y sacar el brazo. Al montar: brazo hasta el tope, XT60, cerrar las levas y
**comprobar a mano que el brazo no gira**. Lista visual antes de cada vuelo: 6 levas cerradas.
EOF
echo ok