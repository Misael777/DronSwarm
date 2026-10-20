# Cableado de los prototipos DS-I y DS-D

- Sprint: S09 · Tarea: S09-05 · Componentes: [seleccion_cots.md](../docs/ingenieria/seleccion_cots.md) · Frames: ADR-011 y ADR-012
- Corrientes de diseño de `engineering/data/results/cots_selection.json`: hover a 4,500 msnm y tope con `MPC_THR_MAX`.

## 1. Corrientes y calibres

| | DS-I (6S) | DS-D (12S) |
|---|---|---|
| Corriente de fase del motor (cable ESC → motor): hover / máxima | 6.4 A / 13.6 A | 16.8 A / 43.6 A (≈ 37 A con `MPC_THR_MAX` = 0.86) |
| Corriente del pack: hover / con empuje 2 × peso / tope | ≈ 15 A / 47 A / 50 A | ≈ 49 A / 167 A / 225 A |
| Cable principal (batería → distribución) | **12 AWG** silicona (≤ 15 cm) | **6 AWG** silicona (≤ 20 cm) |
| Conector de batería | XT90-S (antichispa, 90 A) | AS150U (antichispa, 150 A continuos, 300 A pico, con pin de señal) |
| Distribución de potencia | Placa del ESC 4 en 1 (en la pila de la controladora) | Barra de cobre entre placas, 6 salidas XT60 |
| Cable de motor (ESC → motor) | 18 AWG (vienen del motor) | 14 AWG; extensión 12 AWG hasta el conector XT60 del bloque desmontable |
| Sensado de corriente | Holybro PM02 V3 (60 A) | Sensor Hall de 200 A (sin resistencia en serie) |

Criterio: densidad de corriente ≤ 8 A/mm² en tramos cortos con ventilación de las hélices, y caída de tensión ≤ 1 % en el cable principal.
La corriente de fase del motor es mayor que la de la batería en throttle parcial, porque el ESC baja el voltaje: por eso los cables de motor se dimensionan con la corriente de fase.
El tope de corriente se fija por software (`MPC_THR_MAX`), así que los conectores se dimensionan con el hover y los picos breves.

## 2. Diagrama de bloques

### DS-I

```text
                 ┌───────────────────── Carcasa IP54 ─────────────────────────────────────┐
 Batería 6S2P ──XT90-S──► PM02 V3 ──5.3 V + V/I──► Pixhawk 6C ◄──UART1 (MAVLink)──► Raspberry Pi 5
     │                      │                        │  │  │  │                      │   │   │
     │                      │                        │  │  │  └─UART2──► RFD900x    │   │   └─USB── ESP32-S3 (ESP-NOW)
     │                      │                        │  │  └──── CAN/I2C ─► GNSS F9P + brújula (mástil 15 cm)
     │                      │                        │  └─ UART4 ── ExpressLRS 900 (CRSF)
     │                      │                        └─ UART5/I2C ── MTF-01P (flujo óptico + lidar, mira abajo)
     │                      │                        └─ DShot ×4 + telemetría ──► ESC 4 en 1 50 A ──► 4 motores MN4006
     │                      └──────────────────────────────────────────────────────────────┘
     └── directo (22-25 V) ──► SIYI A8 mini ──Ethernet──► Raspberry Pi 5   (la A8 acepta 11-25.2 V)
                                     └── UART (SIYI/MAVLink) ── Pixhawk (control del gimbal)
 BEC 5 V / 5 A dedicado (desde la batería) ──► Raspberry Pi 5
```

### DS-D

```text
 Batería 12S5P ──AS150U──► sensor Hall 200 A ──► barra de cobre ──XT60 ×6──► 6 ESC APD 120F3 ──XT60 en el bloque──► 6 motores MAD
                                 │                                    └── DShot + telemetría ×6 ◄──────── Pixhawk 6C (AUX/MAIN 1-6)
                                 └── V/I analógico ─► Pixhawk 6C
 Regulador 12S → 5.3 V / 3 A ──► Pixhawk 6C            Regulador 12S → 5 V / 5 A ──► Raspberry Pi 5
 Regulador 12S → 12 V / 3 A ──► SIYI A8 mini (opcional), cámara FPV, 4 LED     Regulador 12S → 7.4 V / 5 A ──► servo de liberación
 Pixhawk 6C: UART1 ↔ Raspberry Pi 5 · UART2 ↔ RFD900x · UART4 ← ExpressLRS · CAN1 ↔ GNSS F9P · I2C ← MTF-01P
             AUX 7 → servo de liberación (función Gripper) · AUX 8 → LED (relé)
 Raspberry Pi 5: GPIO 17 ← micro-interruptor "gancho cerrado" (a masa = cerrado; confirma la entrega, S13-04)
```

## 3. Presupuesto de potencia de la aviónica

| Consumidor | DS-I | DS-D | Alimentación |
|---|---|---|---|
| Pixhawk 6C + GNSS + receptor + flujo óptico | 4 W | 4 W | módulo de potencia 5.3 V |
| Raspberry Pi 5 (pico) | 8 W (12 W) | 8 W (12 W) | BEC 5 V / 5 A dedicado |
| RFD900x (transmitiendo a 1 W) | 5 W | 5 W | 5 V de la Pi o del BEC |
| ESP32-S3 | 1 W | 1 W | USB de la Pi |
| Cámara SIYI A8 mini | 8 W (12 W) | — | batería directa (DS-I) |
| FPV + 4 LED | — | 6 W | 12 V |
| Servo de liberación (al soltar) | — | 15 W pico | 7.4 V |
| **Total continuo** | **≈ 26 W** | **≈ 24 W** | El dimensionamiento supuso 20-25 W ✓ |

## 4. Reglas contra interferencias (GNSS y brújula)

1. GNSS + brújula en un **mástil de 15 cm** sobre la carcasa, lo más lejos posible de la distribución de potencia.
2. Cables de motor y de batería **trenzados** (ida y vuelta juntos): la corriente alterna de los motores induce menos campo.
3. En el DS-D, la barra de cobre va **centrada entre placas, debajo** de la carcasa: lejos del mástil y de la brújula.
4. Ferrita en los cables de señal de los ESC y en el USB de la cámara. Masa en estrella: una sola unión de tierra en el módulo de potencia.
5. Antenas: 900 MHz en vertical, a ≥ 20 cm del GNSS; ExpressLRS a 90° de la RFD900x; 2.4 GHz del ESP32 afuera de la carcasa (la carcasa impresa no apantalla).
6. Calibración de brújula **con los motores a hover** (prueba de interferencia con `MAG_` y `COM_ARM_MAG_ANG`). Criterio: interferencia < 30 % del campo.
7. Pasacables: un solo prensaestopa M12 (DS-I) o M16 (DS-D) para todo lo que entra a la carcasa. Los cables de motor van por dentro de los tubos.

## 5. Conectores y orden de armado

- Batería: conector antichispa, y **siempre la batería al final** del armado, con el dron en tierra y las hélices quitadas en las pruebas de banco.
- Brazos del DS-D: XT60 en el bloque desmontable (macho del lado del motor, hembra del lado del ESC). La fase se fija con el orden de los cables y está codificada en el conector.
- Señales: JST-GH (estándar Pixhawk). Todo cable que cruce el frame va sujeto cada 10 cm y protegido en las aristas de carbono (son cortantes).
