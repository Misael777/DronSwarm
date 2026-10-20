# Servicios de la computadora a bordo (S13-05)

En cada Raspberry Pi 5 (Raspberry Pi OS Lite de 64 bits):

| Servicio | Qué hace |
|---|---|
| `mavlink-router` ([mavlink-router.conf](mavlink-router.conf)) | Une el puerto serie de la Pixhawk (TELEM2) con el nodo del enjambre, las misiones y QGC por red; graba los `.tlog` |
| `dronswarm-node` ([systemd/](systemd/)) | Nodo del enjambre (`control/swarm/node.py`): MAVSDK + red del enjambre + `Agent` del S06 |
| `dronswarm-watchdog` | Reinicia el nodo si se cuelga; PX4 queda en Hold entretanto y el nodo retoma el vuelo al volver |
| `chrony` | Hora sincronizada con el GNSS (PPS si está cableado): la red del enjambre usa marcas de tiempo |

## Instalación

```bash
sudo apt install chrony python3-venv python3-gpiozero
git clone <repo> /opt/dronswarm && cd /opt/dronswarm && python3 -m venv .venv && .venv/bin/pip install -e .
sudo cp control/mavsdk_nodes/mavlink-router.conf /etc/mavlink-router/main.conf
sudo mkdir -p /etc/dronswarm /var/log/dronswarm
echo -e "DRONE_ID=3\nORIGIN=-9.53,-77.05" | sudo tee /etc/dronswarm/node.env      # un ID distinto por dron = MAV_SYS_ID
sudo cp control/mavsdk_nodes/systemd/*.service /etc/systemd/system/
sudo systemctl enable --now mavlink-router dronswarm-node dronswarm-watchdog
```

## Seguridad del enlace

- **PX4 1.15 no implementa la firma MAVLink 2** (se verificó en el código fuente). Mientras tanto:
  - **RFD900x con cifrado AES-128** activado (comando AT de la radio, la misma clave en la estación y en los drones);
  - red Wi-Fi/malla del enjambre con WPA2/WPA3 y una red aislada solo para los drones;
  - la RFD900x de tierra y el receptor de RC con IDs de red y enlace únicos de la flota.
- Cuando se actualice PX4 a una versión con firma (decisión del S16), se activa con una clave por flota cargada en
  cada Pixhawk y en la estación.

## Prueba en el banco (sin hélices, HITL)

1. `systemctl status dronswarm-node` → "conectado a PX4; esperando START".
2. Matar el nodo (`kill -STOP` al proceso, simula un cuelgue) → en ≤ 3 s el watchdog lo reinicia; QGC muestra Hold.
3. En HITL, con el dron "en el aire": el nodo reiniciado escribe "reinicio en vuelo: se retoma el control".
