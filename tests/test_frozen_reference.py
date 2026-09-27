"""Eingefrorene Instanzen (tests/data/uldb_frozen.json): 4 feste ULD-Gewichtslisten (Zahlenwerte, keine
Zufallsziehung zur Testzeit) über verschiedene Fensterbreiten/Gewichtsniveaus/ULD-Zahlen, mit denen alle drei
Verfahren reproduzierbare Kennzahlen liefern müssen.

Nach DEMO-PLAYBOOK Abschnitt 4 (NumPy-Version-Drift) hängt kein Test hier von `np.random.default_rng` zur
Testzeit ab: die Gewichte selbst sind als Zahlen im JSON eingefroren (einmalig mit den Seeds 5/7/3/9 erzeugt
und dann fest gespeichert wie in app.py._live), nur die Verfahren selbst (reine Python-Schleifen plus
CP-SAT) laufen bei jedem Testlauf neu."""
from __future__ import annotations

import json
import pathlib

import pytest

import uldb_constants as C
from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible
from uldb_model import ULD, evaluate_assignment
from uldb_oracle import solve_exact

DATA = json.loads((pathlib.Path(__file__).parent / "data" / "uldb_frozen.json").read_text(encoding="utf-8"))


def _ids():
    return [f"w{c['width']}-{c['level']}-n{c['n_ulds']}-seed{c['seed']}" for c in DATA]


@pytest.mark.parametrize("case", DATA, ids=_ids())
def test_frozen_instance_reproduces_measured_metrics(case):
    ac = C.make_aircraft(case["width"])
    ulds = [ULD(f"u{i}", w) for i, w in enumerate(case["weights"])]

    g_rep = repair_to_feasible(heuristic_greedy(ulds, C.POSITIONS, ac), ulds, C.POS_BY_NAME, ac)
    ev_g = evaluate_assignment(g_rep, ulds, C.POS_BY_NAME, ac)
    b_rep = repair_to_feasible(heuristic_balance(ulds, C.POSITIONS, ac), ulds, C.POS_BY_NAME, ac)
    ev_b = evaluate_assignment(b_rep, ulds, C.POS_BY_NAME, ac)
    cp_assign, status, _ = solve_exact(ulds, C.POSITIONS, ac, time_limit_s=5.0)
    ev_cp = evaluate_assignment(cp_assign, ulds, C.POS_BY_NAME, ac)

    # H_greedy und H_balance sind deterministische reine Python-Verfahren: Zuordnung, cargo_weight UND
    # cg-Werte müssen bitgenau reproduzierbar sein.
    for label, ev in (("greedy", ev_g), ("balance", ev_b)):
        exp = case[label]
        assert ev["cargo_weight"] == pytest.approx(exp["cargo_weight"], rel=1e-9, abs=1e-6)
        assert ev["n_loaded"] == exp["n_loaded"]
        assert ev["feasible"] == exp["feasible"]
        assert ev["cg_full"] == pytest.approx(exp["cg_full"], rel=1e-9, abs=1e-9)
        assert ev["cg_empty"] == pytest.approx(exp["cg_empty"], rel=1e-9, abs=1e-9)

    # CP-SAT: NUR den Zielwert (cargo_weight) und die Zulässigkeit vergleichen, NICHT cg_full/cg_empty - bei
    # mehreren gleich guten Zuordnungen (hier: gleiche Positions-Gewichtsgrenze an allen 10 Positionen, viele
    # Vertauschungen erreichen dasselbe geladene Gewicht) löst ein CP-SAT-Modell mit einzelnem Zielterm
    # Gleichstände nicht deterministisch auf (num_search_workers > 1 kann je nach Timing einen anderen
    # gleichwertigen Optimalpunkt liefern) - siehe DEMO-PLAYBOOK Abschnitt 4 und
    # feedback_cp_sat_lexicographic_tiebreak.md. Genau das war die Ursache einer anfangs beobachteten
    # Flakiness dieses Tests (siehe README "Befunde und Korrekturen gegenüber dem Plan").
    exp_cp = case["exact"]
    assert ev_cp["cargo_weight"] == pytest.approx(exp_cp["cargo_weight"], rel=1e-9, abs=1e-6)
    assert ev_cp["n_loaded"] == exp_cp["n_loaded"]
    assert ev_cp["feasible"] == exp_cp["feasible"]
    assert int(status) == exp_cp["status"]


def test_the_frozen_set_covers_width_and_level_stages():
    widths = {c["width"] for c in DATA}
    levels = {c["level"] for c in DATA}
    assert widths >= {0.5, 0.08, 1.0, 0.3}
    assert levels >= {"gemischt", "leicht", "schwer"}
    assert len(DATA) == 4
