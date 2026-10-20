#!/usr/bin/env python3
"""S13-05 · Watchdog del nodo de enjambre en la computadora a bordo.

El nodo (control/swarm/node.py --heartbeat FILE) escribe un latido 10 veces por segundo. Si el latido tiene más de
HANG_S segundos, el nodo está colgado: el watchdog lo reinicia con systemd. Mientras tanto PX4, sin órdenes de offboard
(COM_OF_LOSS_T = 1 s), queda en Hold (COM_OBL_RC_ACT = 5), y al volver el nodo retoma el vuelo (detecta que está en el aire).
Si el nodo se reinicia más de MAX_RESTARTS veces en 5 min, se deja de reiniciar y queda PX4 a cargo (el piloto ve el
Hold en QGC y decide).

    python3 watchdog.py --heartbeat /run/dronswarm/node.hb --unit dronswarm-node.service
"""

import argparse
import subprocess
import time
from pathlib import Path

HANG_S = 3.0
MAX_RESTARTS = 3
WINDOW_S = 300


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--heartbeat", type=Path, default=Path("/run/dronswarm/node.hb"))
    ap.add_argument("--unit", default="dronswarm-node.service")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    restarts: list[float] = []
    while True:
        time.sleep(1.0)
        try:
            age = time.time() - float(a.heartbeat.read_text())
        except (FileNotFoundError, ValueError):
            continue                                   # el nodo todavía no arrancó
        if age <= HANG_S:
            continue
        restarts = [t for t in restarts if time.time() - t < WINDOW_S]
        if len(restarts) >= MAX_RESTARTS:
            print(f"watchdog: nodo colgado otra vez ({age:.1f} s); se dejan los reinicios, PX4 queda a cargo", flush=True)
            time.sleep(30)
            continue
        print(f"watchdog: latido de hace {age:.1f} s → reinicio de {a.unit}", flush=True)
        restarts.append(time.time())
        if not a.dry_run:
            subprocess.run(["systemctl", "restart", a.unit], check=False)
        a.heartbeat.write_text(f"{time.time():.3f}\n")  # dar tiempo a que arranque


if __name__ == "__main__":
    main()
