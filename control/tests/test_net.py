"""S13-01 · Red del enjambre: transporte local de SITL y radio emulada en el receptor."""

import time

from control.swarm.net import Bus, Emulation


def test_local_transport_reaches_everyone_but_self():
    buses = {k: Bus(k, transport="local", n_nodes=3, local_base=15701) for k in (-1, 0, 1, 2)}
    try:
        buses[0].send("STATE", pos=[0, 0, 10], vel=[0, 0, 0], slot=[0, 0])
        time.sleep(0.05)
        got = {k: [m["src"] for m in b.poll()] for k, b in buses.items()}
        assert got[0] == [] and got[1] == [0] and got[2] == [0] and got[-1] == [0]
    finally:
        for b in buses.values():
            b.close()


def test_emulated_radio_drops_far_messages():
    a = Bus(10, transport="local", n_nodes=12, local_base=15701)
    b = Bus(11, transport="local", n_nodes=12, emulation=Emulation("wifi_24", seed=1), local_base=15701)
    try:
        b.own_pos = (0.0, 0.0, 10.0)
        for _ in range(50):
            a.send("STATE", pos=[5000.0, 0.0, 10.0], vel=[0, 0, 0], slot=[0, 0])     # 5 km: fuera del alcance Wi-Fi
        time.sleep(0.1)
        assert b.poll() == [] and b.dropped == 50
    finally:
        a.close()
        b.close()
