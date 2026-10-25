# S20-07 · Cargador de campo con nitruro de galio (GaN)

> Generado por `electronics/calculo/cargador.py`. Esquema: `electronics/skidl/charger.py`.

Entrada 48 V DC (fuente AC-DC de 1 kW o sistema de 48 V del vehículo/campamento); salida 0-55 V, hasta 20 A, perfil CC/CV leído del BMS del pack por DroneCAN. Etapa reductora-elevadora de 4 interruptores con los mismos medios puentes GaN del ESC del DS-D (EPC2302 + LMG1210) y control digital STM32G474 (HRTIM).

| Punto | Modo | P salida | Pérdidas GaN (250 kHz, 6.8 µH) | Ef. GaN | Pérdidas Si (100 kHz, 15 µH) | Ef. Si |
|---|---|---|---|---|---|---|
| DS-I 6S a 3.9 V/celda | reductor D = 0.49 | 281 W | 6.6 W | 97.7 % | 8.5 W | 97.0 % |
| DS-I 6S fin (CV 4.2 V) | reductor D = 0.53 | 302 W | 6.7 W | 97.8 % | 8.6 W | 97.3 % |
| DS-D 12S a 3.9 V/celda | reductor D = 0.97 | 936 W | 10.1 W | 98.9 % | 14.9 W | 98.4 % |
| DS-D 12S fin (CV 4.2 V) | elevador D = 0.05 | 1008 W | 10.7 W | 99.0 % | 15.9 W | 98.4 % |

## Qué aporta el GaN aquí

- **Calor y tamaño:** a 1 kW la etapa GaN pierde ~10 W contra ~15 W de silicio, con un inductor de 6.8 µH en vez de 15 µH (2.5 × la frecuencia): disipador y caja más chicos, se puede sellar contra el polvo de mina con un ventilador pequeño.
- **Cadena desde la red (AC → pack):** fuente AC-DC (93 %) × etapa GaN = **92.0 %**, contra 91.5 % con silicio y ~88 % del cargador comercial.
- **Campo:** con 48 V de un vehículo o banco solar carga sin inversor (un inversor + cargador pierde 8-12 % más).

## Costo estimado

- Placa DC-DC GaN: US$48 · fuente AC-DC 48 V 1 kW: US$190 · caja, ventilador y conectores: US$25
- **Total ≈ US$263** contra US$380 del cargador comercial (que además no lee el BMS). La fuente AC-DC se compra hecha: diseñar la etapa de red (PFC, aislamiento, certificación eléctrica) no se justifica para este volumen.

## Dentro del pack no se usa GaN

El BMS no conmuta potencia: sus transistores (puerto de carga) están siempre encendidos o apagados, y solo conducen. Ahí cuenta la resistencia de conducción y el precio, no la velocidad de conmutación; un MOSFET de silicio de 100 V y 3.5 mΩ cuesta menos que un GaN equivalente y pierde lo mismo. El GaN va donde se conmuta: ESC del DS-D y cargador.
