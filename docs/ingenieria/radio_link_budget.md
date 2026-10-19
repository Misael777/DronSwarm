# Presupuesto de enlace de radio · prototipos

> Generado por `tools/radio_link_budget.py`. Espacio libre más 6 dB de pérdidas fijas (cables, polarización, cuerpo del dron); el alcance de diseño deja 10 dB de margen para desvanecimiento. **Es teórico**: se mide en campo en el S14 (RSSI y pérdida de paquetes contra distancia).

## 1. Enlaces y márgenes

| Enlace | Uso | Frecuencia | Margen a 2 km | 5 km | 8 km | Alcance (10 dB de margen) | Fresnel a 8 km (60 %) |
|---|---|---|---|---|---|---|---|
| ExpressLRS 900 MHz | control RC (piloto → dron) | 915 MHz | 42 dB | 34 dB | 30 dB | 82 km | 15 m |
| RFD900x | telemetría MAVLink GCS ↔ enjambre (multipunto) | 915 MHz | 53 dB | 45 dB | 41 dB | 293 km | 15 m |
| ESP-NOW (ESP32-S3, modo LR) | estados entre drones (consenso, evitación) | 2440 MHz | 10 dB | 2 dB | -2 dB | 2 km | 9 m |
| Video 2.4 GHz (clase SIYI HM30) | video HD en vivo del dron de inspección (opcional) | 2440 MHz | 24 dB | 16 dB | 12 dB | 10 km | 9 m |

Target del PRD: 5-8 km. **El control RC y la telemetría en 900 MHz llegan con margen.** Sus alcances de 80-290 km son solo de espacio libre: en la práctica los limitan la línea de vista y la curvatura de la Tierra (~15 km a 10 m de altura). El enlace entre drones (ESP-NOW) llega a ~2 km teóricos, ~1 km reales, y basta: los vecinos de una formación están a menos de 50 m (S06). Más lejos, los estados viajan por la malla de 900 MHz. El video en vivo es el enlace más justo: va solo en el dron que inspecciona, y el resto graba a bordo.

## 2. Línea de vista: el problema real es el tajo, no la distancia

A 8 km, la primera zona de Fresnel en 900 MHz mide ~26 m de radio, y despejar su 60 % pide ~15 m sobre el terreno a mitad de camino. La estación de tierra va en alto, en el borde del tajo o sobre un mástil de 6-10 m, y el dron vuela a 30 m o más. Dentro del tajo, la pared corta la señal cuando el dron baja:

| Distancia horizontal al dron (60 m bajo el borde) | Ángulo de bajada | Línea de vista |
|---|---|---|
| 100 m | 31° | despejada si la antena está en el borde mismo del talud |
| 170 m | 19° | la pared del tajo corta la línea de vista: usar un dron repetidor o bajar la estación a un banco |
| 300 m | 11° | la pared del tajo corta la línea de vista: usar un dron repetidor o bajar la estación a un banco |

Medidas de diseño:
- Estación en el borde del talud, del lado de la zona de trabajo. Antena de 900 MHz de 6-9 dBi en un mástil.
- **Dron repetidor:** un DS-I en hover sobre el borde reenvía la telemetría y el video. La malla multipunto del RFD900x lo permite sin otro hardware.
- Si se pierde el enlace, el failsafe de PX4 hace RTL (verificado en SITL, S06). El protocolo entre drones (ADR-010) evita choques mientras tanto.
- Muchas minas grandes tienen **LTE privada**. Un módem LTE en la computadora a bordo daría video y telemetría redundantes; se evalúa con la mina piloto (S15).

## 3. Datos de entrada

- ExpressLRS 900 MHz: documentación ExpressLRS: −112 dBm a 100 Hz (Tx 30 dBm, antenas 2/2 dBi, sensibilidad -112 dBm a 100 Hz (LoRa))
- RFD900x: hoja de datos RFDesign: −121 dBm a 64 kbit/s (Tx 30 dBm, antenas 3/3 dBi, sensibilidad -121 dBm a 64 kbit/s)
- ESP-NOW (ESP32-S3, modo LR): hoja de datos Espressif (modo Long Range) (Tx 20 dBm, antenas 2/2 dBi, sensibilidad -98 dBm a 250 kbit/s)
- Video 2.4 GHz (clase SIYI HM30): estimado de enlaces de video COFDM/Wi-Fi de largo alcance (Tx 27 dBm, antenas 5/9 dBi, sensibilidad -95 dBm a ≈ 8 Mbit/s)

## 4. Regulación (a confirmar en el S22)

- 902-928 MHz y 2.4 GHz son bandas de uso libre en el Perú dentro de los límites de potencia del MTC. Hay que confirmar si 1 W (30 dBm) con antenas de 3-9 dBi entra en el límite de PIRE, o reducir la potencia.
- Los equipos se compran en su versión FCC/CE (por ejemplo, RFD900ux-US) para facilitar la homologación.
