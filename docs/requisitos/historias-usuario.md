# Historias de usuario

- Estado: **Borrador para Gate G0** · Tarea: S02-02 · Fuente: [PRD.md](PRD.md)
- Prioridad MoSCoW: **M** = debe, **S** = debería, **C** = podría, **W** = no en v1.

| ID | Como… | Quiero… | Para… | Prio | Misión |
|---|---|---|---|---|---|
| HU-01 | topógrafo | levantar el tajo completo en un turno | actualizar el modelo de mina a diario | M | M1 |
| HU-02 | ingeniero de geotecnia | inspeccionar taludes de cerca sin exponer personal | detectar grietas y desprendimientos a tiempo | M | M2 |
| HU-03 | supervisor de mantenimiento | recorrer la faja sin detenerla | encontrar idlers dañados antes de una falla | M | M3 |
| HU-04 | ingeniero de relaves | un mapeo mensual comparable mes a mes | vigilar la presa y el espejo de agua | M | M4 |
| HU-05 | jefe de perforación y voladura | el modelo post-voladura en menos de 30 min | reanudar la operación antes | S | M5 |
| HU-06 | almacenero | enviar un repuesto de 5 kg al frente | evitar viajes de camioneta y tiempo muerto | M | D1 |
| HU-07 | geólogo | enviar muestras al laboratorio | acelerar los resultados de ley | S | D2 |
| HU-08 | piloto | controlar 6 drones a la vez | cubrir más área con una sola persona | M | E1 |
| HU-09 | jefe de seguridad | que cualquier falla termine en RTL o aterrizaje seguro | operar sin riesgo para el personal | M | Todas |
| HU-10 | jefe de seguridad | geocercas definidas por la mina | que ningún dron entre en zonas prohibidas | M | Todas |
| HU-11 | gerente de operaciones | procesar datos sin licencias anuales | bajar el costo total frente a DJI | M | M1-M5 |
| HU-12 | técnico de mantenimiento de drones | cambiar motor, hélice o batería en minutos | reducir el tiempo fuera de servicio | S | Todas |
| HU-13 | operador | volar en minas subterráneas | inspeccionar galerías | W | v2 |

## Criterios de aceptación (Dado / Cuando / Entonces)

**HU-01 · Levantamiento del tajo**
- Dado un polígono de 60 ha a 4,500 msnm y viento ≤ 8 m/s,
- cuando el operador lanza la misión de grilla a 100 m AGL,
- entonces un DS-I lo completa en un vuelo con GSD ≤ 3 cm/px, y ODM entrega una ortofoto con error horizontal ≤ 5 cm en los puntos de control.

**HU-02 · Inspección de taludes**
- Dado un talud de 300 m de largo,
- cuando se ejecuta la misión de fachada a 30 m,
- entonces las imágenes tienen GSD ≤ 1 cm/px y se distingue una grieta de 2 cm en el informe.

**HU-03 · Faja transportadora**
- Dado el trazado de 3 km de una faja en operación,
- cuando se ejecuta la misión de corredor,
- entonces se obtiene video 4K georreferenciado de toda la faja en un vuelo, sin acercarse a menos de 10 m de la estructura.

**HU-04 · Relaves**
- Dados dos vuelos con un mes de diferencia sobre la misma presa,
- cuando se comparan los DEM en ODM,
- entonces la diferencia en zonas sin cambios es ≤ 5 cm (RTK + puntos de control).

**HU-05 · Post-voladura**
- Dado un disparo terminado y la zona liberada,
- cuando se lanza la misión preconfigurada,
- entonces el modelo 3D está disponible en ≤ 30 min.

**HU-06 · Delivery de repuesto**
- Dado un paquete de 5 kg en la caja estándar y un destino a 3 km a 4,500 msnm,
- cuando el almacenero confirma el envío,
- entonces el DS-D entrega, libera la carga, confirma y regresa con ≥ 20 % de batería.

**HU-07 · Muestras**
- Dada una caja sellada de 2-5 kg,
- cuando se envía al laboratorio,
- entonces llega sin abrirse y el registro de entrega queda en la bitácora.

**HU-08 · Enjambre**
- Dada un área dividida entre 6 drones,
- cuando el operador lanza la misión,
- entonces el sistema asigna sectores, separa altitudes, no hay conflictos de distancia < 10 m entre drones y el operador puede abortar todo con un botón.

**HU-09 · Failsafes**
- Dado un dron en misión,
- cuando ocurre batería baja, pérdida de enlace, pérdida de GNSS o (en DS-D) un motor caído,
- entonces ejecuta RTL o aterrizaje seguro según la tabla de failsafes, sin intervención del operador.

**HU-10 · Geocerca**
- Dada una geocerca cargada por la mina,
- cuando una ruta la cruza,
- entonces DS-GCS rechaza la misión, y si en vuelo el dron se acerca al límite, se detiene y regresa.

**HU-11 · Procesamiento sin licencias**
- Dado un set de imágenes de un vuelo de M1,
- cuando se procesa en DS-GCS,
- entonces se obtienen ortofoto, DEM, nube de puntos y volumen de stockpile sin software de pago.

**HU-12 · Mantenimiento**
- Dado un dron con un motor dañado,
- cuando el técnico lo cambia con la herramienta estándar,
- entonces el cambio toma ≤ 10 min y el dron pasa la prueba de prevuelo.
