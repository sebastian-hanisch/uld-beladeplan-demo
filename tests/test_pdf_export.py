"""Tests für uldb_pdf_export.py: das PDF muss ohne Fehler entstehen (keine der abstürzenden Sonderzeichen
Gedankenstrich/Euro, siehe DEMO-PLAYBOOK Abschnitt 7) und ein plausibles PDF-Objekt sein."""
import numpy as np

import uldb_constants as C
import uldb_results as R
from uldb_heuristics import heuristic_balance, heuristic_greedy, repair_to_feasible
from uldb_model import ULD, evaluate_assignment
from uldb_oracle import solve_exact
from uldb_pdf_export import generate_uldb_pdf

DATA = R.load_results()


def _live(width=0.5, n_ulds=12, level="gemischt", seed=0):
    ac = C.make_aircraft(width)
    lo, hi = C.WEIGHT_LEVELS[level]
    rng = np.random.default_rng(seed)
    ulds = [ULD(f"u{i}", float(rng.uniform(lo, hi))) for i in range(n_ulds)]
    g = repair_to_feasible(heuristic_greedy(ulds, C.POSITIONS, ac), ulds, C.POS_BY_NAME, ac)
    b = repair_to_feasible(heuristic_balance(ulds, C.POSITIONS, ac), ulds, C.POS_BY_NAME, ac)
    cp, _, _ = solve_exact(ulds, C.POSITIONS, ac, time_limit_s=2.0)
    return dict(
        ulds=ulds, ac=ac, assign_greedy=g, assign_balance=b, assign_exact=cp,
        ev_greedy=evaluate_assignment(g, ulds, C.POS_BY_NAME, ac),
        ev_balance=evaluate_assignment(b, ulds, C.POS_BY_NAME, ac),
        ev_exact=evaluate_assignment(cp, ulds, C.POS_BY_NAME, ac),
    )


def test_pdf_wird_erzeugt_und_beginnt_mit_pdf_signatur():
    live = _live()
    cell = R.find_cell(DATA, 0.5, "gemischt", 12)
    data = generate_uldb_pdf(dict(width=0.5, n_ulds=12, level="gemischt", seed=0), live, cell)
    assert isinstance(data, (bytes, bytearray))
    assert data[:5] == b"%PDF-"
    assert len(data) > 500


def test_pdf_funktioniert_ohne_geladene_ulds():
    """Grenzfall: eine Instanz, in der (fast) nichts geladen wurde, darf das PDF nicht zum Absturz bringen -
    sehr enges Fenster, wenige, schwere ULDs."""
    live = _live(width=0.08, n_ulds=8, level="schwer", seed=1)
    cell = R.find_cell(DATA, 0.08, "schwer", 8)
    data = generate_uldb_pdf(dict(width=0.08, n_ulds=8, level="schwer", seed=1), live, cell)
    assert data[:5] == b"%PDF-"


def test_pdf_funktioniert_fuer_engstes_fenster():
    live = _live(width=0.08)
    cell = R.find_cell(DATA, 0.08, "gemischt", 12)
    data = generate_uldb_pdf(dict(width=0.08, n_ulds=12, level="gemischt", seed=0), live, cell)
    assert data[:5] == b"%PDF-"
