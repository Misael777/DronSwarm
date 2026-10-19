# Banco de empuje y torque (S10-02)

Mide, para cada combinación motor + hélice + ESC: **empuje, torque, rpm, voltaje, corriente y temperatura** contra
el throttle. Con eso se obtienen los datos que hoy son estimados (Kv, Rm, I0, corriente máxima) y los coeficientes
reales de la hélice. Esos datos reemplazan al modelo en el dimensionamiento, la selección COTS y el simulador.

```text
  firmware/bench/bench.ino   ESP32: lee las celdas de carga, rpm, V/I y la telemetría del ESC; manda PWM al ESC
  tools/bench/acquire.py     PC: corre las secuencias de ensayo por USB-serial y guarda CSV en data/bench/
  tools/bench/analyze.py     PC: ajusta Kv, Rm, I0, CT y CP, corrige por altitud e informa (docs/ingenieria/motor_cots_report.md)
```

## 1. Mecánica

```text
        hélice (empuja hacia ARRIBA: el aire va hacia abajo, lejos de la mesa)
          ║
      ┌───╨───┐  motor sobre placa DMI (la misma interfaz del frame)
      │ placa │◄── 2 celdas de 5 kg bajo la placa, a ±40 mm del eje: su diferencia × brazo = TORQUE
      └───┬───┘
          │ columna de aluminio 30×30
   ┌──────┴──────┐  palanca 1:1 sobre pivote de rodamientos
   │   celda 20 kg   │  ── EMPUJE (DS-D llega a ~9 kgf; la celda de 20 kg deja margen)
   └─────────────┘
   base de MDF/aluminio de 60 × 60 cm, ATORNILLADA a una mesa pesada o al piso
```

- **Altura libre bajo la hélice ≥ 1 diámetro**, y nada delante del disco: la mesa cerca de la hélice falsea el empuje (efecto suelo).
- **Escudo de policarbonato de 4 mm** alrededor del plano de la hélice. Nadie se para en ese plano mientras gira.
- **Parada de emergencia** cableada que corta la batería (contactor o antichispa con lazo), además del comando `S` del firmware.
- Hélices de 26" del DS-D: girarlas solo en exteriores o en un ambiente de 3 m o más de alto, con el banco anclado.

## 2. Electrónica (≈ US$180)

| Componente | Uso |
|---|---|
| ESP32 DevKit (WROOM-32) | Adquisición a 50 Hz y PWM al ESC (50 Hz, 1000-2000 µs) |
| 3 × HX711 + celdas de carga: 1 × 20 kg (empuje), 2 × 5 kg (torque) | Fuerzas |
| Sensor óptico reflectivo (TCRT5000) + cinta reflectiva en el buje | rpm de referencia (1 pulso por vuelta) |
| INA228 + shunt de 200 A / 75 mV | Voltaje y corriente de precisión (lado batería) |
| Telemetría del ESC (KISS/BLHeli32 por UART) | eRPM, corriente, voltaje y temperatura del ESC (contraste) |
| Termocupla tipo K + MAX31855 | Temperatura del bobinado (pegada al estator) |
| Batería de ensayo (la del dron) o fuente ≥ 1.5 kW para 12S | Energía |

Conexiones del ESP32 (definidas en `bench.ino`): HX711 empuje DOUT 32 / SCK 33, torque A 25 / 26, torque B 27 / 14 ·
PWM al ESC GPIO 18 · rpm GPIO 34 · I2C (INA228) 21/22 · UART2 telemetría ESC RX 16 · MAX31855 SPI CS 5 (SCK 19, SO 23).

## 3. Calibración (antes de cada campaña)

1. **Celdas:** cero sin carga (`Z`), luego masa patrón de 2 kg en el punto de empuje y de 1 kg en cada celda de torque.
   `acquire.py calibrate` calcula los factores y los guarda en `data/bench/calibracion.json`.
2. **Corriente:** compararla con una pinza DC a 10 A y a 30 A. Si difiere más de 2 %, ajustar el shunt en la calibración.
3. **rpm:** comparar el sensor óptico con la eRPM del ESC dividida por los pares de polos. Deben coincidir dentro de 1 %.

## 4. Ensayos (ver `tools/bench/acquire.py --help`)

| Ensayo | Qué mide | Cómo |
|---|---|---|
| `noload` | Kv e I0 | Sin hélice: 20 → 80 % de throttle; Kv = rpm / V, I0 = corriente sin carga |
| `sweep` | Curvas de empuje, torque, potencia y eficiencia; CT y CP de la hélice; Rm | Con hélice: 5 → 100 % en pasos de 5 %, 4 s por paso (promedio de los últimos 2 s); corta solo si pasa la corriente o la temperatura |
| `hover` | Temperatura y estabilidad en hover | Empuje fijo = peso del dron / n a 4,500 msnm, corregido a la densidad del lugar, durante 10 min |

Criterios de aceptación de cada motor (S10-03): Kv dentro de ±5 % del catálogo; empuje en hover con corriente ≤ la del
modelo + 10 %; temperatura del estator ≤ 80 °C tras 10 min en hover; ninguna vibración anómala (sin resonancias en la placa).

## 5. Corrección por altitud (S10-04)

A igual rpm, el empuje y el torque son proporcionales a la densidad del aire (CT y CP son coeficientes adimensionales).
El banco mide CT y CP donde esté (por ejemplo, Lima, ρ ≈ 1.19 kg/m³), y `analyze.py` calcula en la altura de trabajo
(4,500-5,000 msnm, ρ ≈ 0.65-0.74) qué rpm, corriente y potencia hacen falta para el hover y si queda margen de empuje.
Lo que la corrección no cubre: el número de Reynolds más bajo en altura empeora un poco CT y CP. El modelo del S03 lo
estima, y la prueba de campo del S15 lo confirma.
