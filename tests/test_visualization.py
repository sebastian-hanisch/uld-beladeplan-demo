"""Rauchtests für uldb_visualization.py: Figuren bauen ohne Fehler, mit der erwarteten Spurenzahl, und alle
Achsen sind fixedrange (Plotly-Fallstricke, DEMO-PLAYBOOK Abschnitt 3)."""
import numpy as np
import plotly.graph_objects as go

import uldb_constants as C
import uldb_results as R
import uldb_visualization as V
from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible
from uldb_model import ULD, evaluate_assignment
from uldb_oracle import solve_exact

DATA = R.load_results()


def _sample_live(width=0.5, level="gemischt", n_ulds=12, seed=0):
    ac = C.make_aircraft(width)
    lo, hi = C.WEIGHT_LEVELS[level]
    rng = np.random.default_rng(seed)
    ulds = [ULD(f"u{i}", float(rng.uniform(lo, hi))) for i in range(n_ulds)]
    g = repair_to_feasible(heuristic_greedy(ulds, C.POSITIONS, ac), ulds, C.POS_BY_NAME, ac)
    b = repair_to_feasible(heuristic_balance(ulds, C.POSITIONS, ac), ulds, C.POS_BY_NAME, ac)
    cp, _, _ = solve_exact(ulds, C.POSITIONS, ac, time_limit_s=2.0)
    evs = {
        "greedy": evaluate_assignment(g, ulds, C.POS_BY_NAME, ac),
        "balance": evaluate_assignment(b, ulds, C.POS_BY_NAME, ac),
        "exact": evaluate_assignment(cp, ulds, C.POS_BY_NAME, ac),
    }
    return ulds, {"greedy": g, "balance": b, "exact": cp}, evs, ac


def test_loading_map_figure_hat_drei_balken_und_sechs_marker_spuren():
    ulds, assigns, evs, ac = _sample_live()
    fig = V.loading_map_figure(ulds, assigns, evs, ac)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 3 + 6  # 3 Balken (je Verfahren) + 6 CG-Marker (voll/leer je Verfahren)
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange


def test_loading_map_figure_funktioniert_ohne_geladene_ulds():
    empty_assign = {}
    ev_empty = evaluate_assignment(empty_assign, [], C.POS_BY_NAME, C.make_aircraft(0.5))
    fig = V.loading_map_figure([], {"greedy": {}, "balance": {}, "exact": {}},
                                {"greedy": ev_empty, "balance": ev_empty, "exact": ev_empty}, C.make_aircraft(0.5))
    assert isinstance(fig, go.Figure)


def test_gap_over_width_figure_hat_zwei_balkenspuren_und_fixedrange():
    rows = R.width_rows(DATA, "gemischt", 12)
    fig = V.gap_over_width_figure(rows)
    assert len(fig.data) == 2
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange


def test_regime_figure_deckt_alle_45_zellen_ab():
    rows = R.regime_rows(DATA)
    fig = V.regime_figure(rows)
    assert len(fig.data[0].x) == 45
    assert fig.layout.xaxis.fixedrange and fig.layout.yaxis.fixedrange
