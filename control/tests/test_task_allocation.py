"""S13-02 · Asignación de tareas y capas de altitud."""

import pytest

from control.swarm.task_allocation import Drone, Task, altitude_layers, auction, hungarian


def fleet():
    return [Drone(0, "DS-I", (0, 0), 200, 6.0, camera=True), Drone(1, "DS-I", (0, 50), 200, 6.0, camera=True),
            Drone(2, "DS-D", (0, 100), 800, 30.0, payload_kg=5.0)]


def test_hungarian_respects_capabilities_and_distance():
    tasks = [Task("sector_far", "survey", (500, 50), work_wh=40, needs_camera=True),
             Task("sector_near", "survey", (100, 0), work_wh=40, needs_camera=True),
             Task("repuesto", "deliver", (800, 100), work_wh=20, payload_kg=5.0)]
    p = hungarian(fleet(), tasks)
    assert p.assignment[2] == ["repuesto"]                       # solo el DS-D lleva carga
    assert set(p.assignment[0] + p.assignment[1]) == {"sector_far", "sector_near"}
    assert not p.unassigned


def test_energy_reserve_makes_task_infeasible():
    p = hungarian(fleet(), [Task("lejos", "deliver", (20000, 0), payload_kg=5.0)])
    assert p.unassigned == ["lejos"]                              # 40 km ida y vuelta > energía útil


def test_auction_gives_several_tasks_per_drone():
    tasks = [Task(f"s{k}", "inspect", (100 * k, 0), work_wh=10, needs_camera=True) for k in range(1, 6)]
    p = auction(fleet(), tasks)
    assert sum(len(v) for v in p.assignment.values()) == 5 and 2 not in p.assignment


def test_crossing_routes_get_different_layers():
    routes = {0: ((0, 0), (100, 100)), 1: ((0, 100), (100, 0)), 2: ((0, 300), (100, 300))}
    layers = altitude_layers(routes)
    assert layers[0] != layers[1]                                 # se cruzan
    assert layers[2] == pytest.approx(30.0)                       # lejos: capa base
