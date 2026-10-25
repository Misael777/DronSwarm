# S20-07 · Packs de batería propios 21700 y BMS

> Generado por `electronics/calculo/baterias.py`. BMS: `electronics/skidl/bms.py` (netlists `bms_ds_i`, `bms_ds_d`). Cargador: `S20-07_cargador.md`.

| | DS-I | DS-D |
|---|---|---|
| Configuración | 6S2P Samsung INR21700-50S | 12S5P Molicel INR21700-P42A |
| Celdas | 12 | 60 |
| Tensión nominal / máx. [V] | 21.6 / 25.2 | 43.2 / 50.4 |
| Capacidad [Ah] | 10.0 | 21.0 |
| Energía [Wh] | 216.0 | 907.0 |
| Masa estimada [kg] | 1.0 | 4.73 |
| Energía específica [Wh/kg] | 217.0 | 192.0 |
| Corriente del dron: hover / pico 30 s [A] | 21.8 / 42.4 | 82.2 / 163.4 |
| Por celda: hover / pico / máx. de la celda [A] | 10.9 / 21.2 / 25 | 16.4 / 32.7 / 45 |
| Margen de la celda en el pico | 1.18 | 1.38 |
| Caída de tensión del pack en el pico [V] | 1.78 | 4.71 |
| Pérdida interna en hover [W] | 20.0 | 194.6 |
| Conexión entre grupos | níquel puro 0.15 × 8.0 mm ×2 | cobre 0.2 × 10.0 mm ×1 + níquel puro 0.15 × 10.0 mm ×1 |
| Densidad en la conexión: hover / pico [A/mm²] | 4.5 / 8.8 | 4.7 / 9.3 |
| Fusible principal [A] | 60 | 200 |
| Cable | 10 AWG silicona (5.26 mm²) | 6 AWG silicona (13.3 mm²) |
| Conector de vuelo | XT90-S (antichispa) | AS150U (antichispa) |
| Carga [A] (C) | 12 (1.2 C) | 20 (0.95 C) |
| Costo de materiales [US$] | 99.0 | 330.0 |

## Decisiones

- **Salida de vuelo sin transistor de corte.** Un BMS que corta en vuelo derriba el dron. El BMS mide y avisa a PX4 por DroneCAN (BatteryInfo: tensión de cada celda, corriente, temperatura, estado de carga); PX4 hace RTL o aterriza. La protección contra cortocircuito es el fusible principal. El puerto de **carga** sí se corta (MOSFET CHG/DSG del BQ769x0) por sobretensión, sobretemperatura o falla.
- **Balanceo externo de ~100 mA** (P-MOSFET por celda): el interno del BQ76930/40 es de pocos mA y no alcanza para 10-21 Ah.
- **Conexiones:** en el DS-I alcanza níquel puro doble; en el DS-D la corriente de pico (≈ 33 A por celda) pide cobre de 0.2 mm bajo el níquel (sándwich soldado por puntos), como se previó en el S09.
- **Shunt de barra fuera de la placa**, con hilos Kelvin: la corriente de vuelo no pasa por el BMS.
- **GaN no:** el BMS no conmuta potencia (ver `S20-07_cargador.md`); el GaN va en el cargador.
- **Calor del pack del DS-D:** 195 W en hover (3.2 W por celda) por la resistencia interna. Con el aire de 5,000 msnm (~50 % de densidad) el pack necesita canales de aire entre filas y toma de aire de las hélices; las NTC del BMS limitan la potencia vía PX4 por encima de 55 °C.
- **Margen del DS-I en el pico:** 1.18 × la corriente máxima de la 50S. Alcanza para 30 s, pero si el banco muestra calentamiento se pasa a P45B (45 A) con el mismo armado.

## Proceso de armado (soldadura por puntos)

1. Recepción: celdas de distribuidor autorizado con 2 cotizaciones; medir tensión y resistencia interna (1 kHz) de cada celda; formar grupos en paralelo con ΔV ≤ 10 mV y ΔR ≤ 5 %.
2. Portaceldas impresos (ASA, resistente a 80 °C) y aisladores de papel de pescado en el polo positivo.
3. Soldadura por puntos (soldadora de condensador, banco S21): 2 puntos dobles por celda y capa; probar arrancando una tira de prueba en cada sesión.
4. En el DS-D, cobre de 0.2 mm abajo y níquel encima (el níquel suelda al cobre y a la celda).
5. Arnés de balanceo con fusible de hilo (o resistencia 0 Ω de 1206) en cada toma; NTC pegadas al centro del pack.
6. BMS, shunt, fusible y conectores; prueba: tensiones por celda en el BMS, balanceo, corte del puerto de carga, lectura en PX4 por DroneCAN.
7. Caja con espuma, termocontraíble y etiqueta (Wh, número de serie, fecha). Primer ciclo completo en el banco.

## Costo de materiales por pack

| Ítem | DS-I | DS-D |
|---|---|---|
| Celdas | US$54 | US$240 |
| BMS (placa propia, materiales) | US$22 | US$30 |
| Shunt de barra 4 terminales | US$4 | US$9 |
| Fusible + porta | US$4 | US$12 |
| Conectores (descarga, carga XT30/XT60, balanceo) | US$6 | US$11 |
| Níquel / cobre, papel aislante, cinta Kapton | US$3 | US$12 |
| Caja impresa (ASA) + espuma + termocontraíble | US$4 | US$10 |
| Cable de silicona | US$2 | US$6 |
| **Total** | **US$99** | **US$330** |

Precios estimados (celdas: engineering/battery.py; resto a 10 unidades), se cotizan en E7.
