"""S06 · Formaciones, consenso, evitación, modelo de radio y escenario completo (simulador cinemático)."""

import numpy as np
import pytest

from control.swarm import formation
from control.swarm.avoidance import AvoidParams, Obstacle, avoid
from control.swarm.consensus import FormationGains, NeighborState, formation_velocity
from control.swarm.sim_kinematic import run_once
from control.swarm.swarm import Agent
from simulation.common.comms_model import RADIOS, CommsModel


@pytest.mark.parametrize("shape", list(formation.SHAPES))
def test_shapes_are_centered_and_spaced(shape):
    off = formation.make(shape, 6, 6.0)
    assert off.shape == (6, 2)
    assert np.allclose(off.mean(axis=0), 0.0, atol=1e-9)
    assert formation.min_spacing(off) >= 3.0


def test_to_world_rotates_forward_axis():
    off = np.array([[1.0, 0.0]])                     # 1 m adelante
    assert np.allclose(formation.to_world(off, np.pi / 2), [[0.0, 1.0]])   # rumbo norte → +y


def test_assign_is_optimal_permutation():
    slots = formation.line(4, 5.0)
    pos = slots[[2, 0, 3, 1]] + 0.1
    perm = formation.assign(pos, slots)
    assert sorted(perm) == [0, 1, 2, 3]
    assert np.allclose(slots[perm], slots[[2, 0, 3, 1]])


def test_consensus_pulls_toward_reference_and_neighbors():
    g = FormationGains()
    v, info = formation_velocity(0.0, np.array([0.0, 0.0, 10.0]), np.zeros(2), np.array([4.0, 0.0]), np.zeros(2), {}, 10.0, g)
    assert v[0] > 0 and abs(v[1]) < 1e-9 and info["neighbors"] == 0
    nb = {1: NeighborState(np.array([0.0, 6.0, 10.0]), np.zeros(3), np.zeros(2), 0.0)}
    v2, _ = formation_velocity(0.0, np.array([0.0, 0.0, 10.0]), np.zeros(2), np.zeros(2), np.zeros(2), nb, 10.0, g)
    assert v2[1] > 0                                 # el vecino "cree" que el centro está al norte


def test_stale_neighbor_is_ignored():
    g = FormationGains(stale_s=1.0)
    nb = {1: NeighborState(np.array([0.0, 6.0, 10.0]), np.zeros(3), np.zeros(2), 0.0)}
    _, info = formation_velocity(5.0, np.zeros(3), np.zeros(2), np.zeros(2), np.zeros(2), nb, 0.0, g)
    assert info["neighbors"] == 0


def test_leader_follower_holds_without_leader():
    g = FormationGains()
    v, info = formation_velocity(0.0, np.array([1.0, 1.0, 10.0]), np.zeros(2), None, np.zeros(2), {}, 10.0, g, mode="leader")
    assert not info["leader_ok"] and np.allclose(v, 0.0)


def test_head_on_conflict_turns_right():
    p = AvoidParams()
    pos, vel = np.array([0.0, 0.0, 10.0]), np.array([0.0, 4.0, 0.0])          # voy al norte
    other = (np.array([0.0, 12.0, 10.0]), np.array([0.0, -4.0, 0.0]))       # viene de frente
    v, info = avoid(pos, vel, np.array([0.0, 4.0, 0.0]), [other], [], p)
    assert v[0] > 0.5                                # se desvía al este = su derecha
    assert info["active"]


def test_vertical_separation_ignores_conflict():
    p = AvoidParams()
    other = (np.array([0.0, 2.0, 20.0]), np.zeros(3))
    v, _ = avoid(np.array([0.0, 0.0, 10.0]), np.zeros(3), np.array([0.0, 3.0, 0.0]), [other], [], p)
    assert np.allclose(v[:2], [0.0, 3.0])


def test_obstacle_in_path_is_bypassed_without_stopping():
    p = AvoidParams()
    v, _ = avoid(np.array([0.3, 0.0, 10.0]), np.array([0.0, 4.0, 0.0]), np.array([0.0, 4.0, 0.0]), [],
                 [Obstacle(0.0, 7.0, 1.0)], p)
    assert np.linalg.norm(v[:2]) > 3.0               # no se frena (sin mínimo local)
    assert v[0] > 1.0                                # rodea por el lado en que ya está (este)


def test_comms_range_and_loss():
    net = CommsModel(RADIOS["wifi_24"], seed=1)
    r = net.range_m()
    assert 200 < r < 3000
    near = sum(net.send(0, 1, 0.0, (0, 0, 10), (20, 0, 10)) for _ in range(300))
    far = sum(net.send(0, 2, 0.0, (0, 0, 10), (3 * r, 0, 10)) for _ in range(300))
    assert near > 280 and far < 30
    msgs = net.deliver(1.0)
    assert len(msgs) == near + far and all(0 < m.age < 0.2 for m in msgs)


def test_comms_extra_loss_and_down_nodes():
    net = CommsModel(RADIOS["mesh_900"], seed=2, extra_loss=0.3)
    got = sum(net.send(0, 1, 0.0, (0, 0, 10), (50, 0, 10)) for _ in range(2000))
    assert 0.25 < 1 - got / 2000 < 0.35
    net.down.add(1)
    assert not net.send(0, 1, 0.0, (0, 0, 10), (50, 0, 10))


def test_lost_link_agent_stops_and_climbs():
    a = Agent(0)
    a.receive(1, NeighborState(np.array([10.0, 0.0, 10.0]), np.zeros(3), np.zeros(2), 0.0))
    v, info = a.command(2.0, np.array([0.0, 0.0, 10.0]), np.zeros(3), np.zeros(2), np.array([20.0, 0.0]),
                        np.array([4.0, 0.0]), 10.0, [])
    assert info.get("lost_link") and np.allclose(v[:2], 0.0) and v[2] > 0


def test_full_scenario_kinematic_no_collisions():
    r = run_once(seed=3)
    assert r["completed"]
    assert r["collisions"] == 0
    assert r["min_separation_m"] > 1.1
    assert r["min_obstacle_clearance_m"] > 1.0
    assert [p["phase"] for p in r["phases"]] == ["formar_v", "transito_v", "circulo", "cruce", "linea_regreso"]


def test_monitor_analysis_counts_contacts(tmp_path):
    from control.swarm.analyze_monitor import analyze

    csv = tmp_path / "monitor.csv"
    csv.write_text("t,model,x,y,z\n"
                   "1.0,ds_i_0,0,0,10\n1.0,ds_i_1,3,0,10\n1.0,#pair,ds_i_0|ds_i_1,3.0,0\n1.0,#obst,ds_i_0|torre,5.2,0\n"
                   "2.0,ds_i_0,0,0,10\n2.0,ds_i_1,0.8,0,10\n2.0,#pair,ds_i_0|ds_i_1,0.8,0\n2.0,#contact,ds_i_0|ds_i_1,0,0\n")
    r = analyze(csv)
    assert r["collisions"] == 1 and r["min_separation_m"] == 0.8 and r["min_separation_t_s"] == 2.0
    assert r["min_obstacle_clearance_m"] == 5.2 and r["drones"] == ["ds_i_0", "ds_i_1"]
