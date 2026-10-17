"""Consistencia del plan de trabajo: IDs, dependencias, entregables y Gates."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plan"))
import plan_data as D  # noqa: E402

TASK_IDS = [f"{s['id']}-{k:02d}" for s in D.SPRINTS for k in range(1, len(s["tasks"]) + 1)]
SPRINT_IDS = [s["id"] for s in D.SPRINTS]


def test_ids_unique():
    assert len(TASK_IDS) == len(set(TASK_IDS))
    assert len(SPRINT_IDS) == len(set(SPRINT_IDS))


def test_dependencies_exist_and_point_backwards():
    for s in D.SPRINTS:
        for k, task in enumerate(s["tasks"], start=1):
            tid = f"{s['id']}-{k:02d}"
            for dep in re.findall(r"S\d\d-\d\d", task[5]):
                assert dep in TASK_IDS, f"{tid} depende de {dep}, que no existe"
                assert dep < tid, f"{tid} depende de {dep}, que es posterior"


def test_deliverables_point_to_tasks():
    for name, _kind, _path, task in D.DELIVERABLES:
        assert task in TASK_IDS, f"entregable '{name}' apunta a {task}, que no existe"


def test_gates_match_sprints():
    gates = {g[0]: g[2] for g in D.GATES}
    for s in D.SPRINTS:
        if s["gate"]:
            assert gates.get(s["gate"]) == s["id"]


def test_phases_and_priorities_valid():
    phases = {code for code, _ in D.PHASES}
    for s in D.SPRINTS:
        assert s["phase"] in phases
        for task in s["tasks"]:
            assert task[3] in {"Alta", "Media", "Baja"}
            assert task[4] > 0


def test_sprints_within_capacity():
    for s in D.SPRINTS:
        hours = sum(t[4] for t in s["tasks"])
        assert hours <= D.CAPACITY_H, f"{s['id']} tiene {hours} h > {D.CAPACITY_H} h"


def test_regeneration_preserves_progress(tmp_path):
    import generar_plan_trabajo as G
    from openpyxl import load_workbook

    xlsx = tmp_path / "plan.xlsx"
    G.build_xlsx(xlsx, updates=["S01-01=Hecho:3", "S01-04=En curso:10:0.6"])
    G.build_xlsx(xlsx, saved=G.collect_inputs(xlsx))
    t = load_workbook(xlsx)["Tareas"]
    rows = {t[f"A{r}"].value: r for r in range(2, t.max_row + 1)}
    assert t[f"K{rows['S01-01']}"].value == "Hecho"
    assert t[f"N{rows['S01-01']}"].value == 3
    assert t[f"K{rows['S01-04']}"].value == "En curso"
    assert t[f"L{rows['S01-04']}"].value == 0.6
