"""Jede Zahl aus dem README wird hier gegen data/uldb_results.json nachgerechnet (DEMO-PLAYBOOK Abschnitt 4:
erst messen, dann Text schreiben - keine Behauptung ohne Test)."""
import pytest

import uldb_results as R

D = R.load_results()
REF = R.find_cell(D, 0.5, "gemischt", 12)
MITTEL = R.find_cell(D, 0.3, "gemischt", 12)
TIGHT = R.find_cell(D, 0.08, "gemischt", 12)
EXTREME = R.find_cell(D, 0.08, "gemischt", 8)


def test_befund_regel_ohne_balance_verletzt_oft():
    assert REF["violation_rate_greedy_raw"] == pytest.approx(0.6875)
    assert MITTEL["violation_rate_greedy_raw"] == pytest.approx(1.0)


def test_befund_wirtschaftlicher_preis_waechst_mit_enge():
    assert REF["gap_greedy_pct"] == pytest.approx(10.304432391282711, rel=1e-9)
    assert TIGHT["gap_greedy_pct"] == pytest.approx(43.552541113944415, rel=1e-9)
    assert EXTREME["gap_greedy_pct"] == pytest.approx(55.28586683219127, rel=1e-9)


def test_befund_h_balance_fast_immer_optimal():
    gb = R.gap_balance_summary(D)
    assert gb["n_zero"] == 42
    assert gb["n_total"] == 45


def test_befund_h_balance_nicht_bewiesen_optimal():
    gb = R.gap_balance_summary(D)
    assert gb["max_gap"] == pytest.approx(2.380606130145444, rel=1e-9)
    assert gb["max_cell"]["width"] == pytest.approx(0.08)
    assert gb["max_cell"]["level"] == "gemischt" and gb["max_cell"]["n_ulds"] == 12


def test_befund_zwei_zeitpunkte_effekt_ist_real_aber_nie_umgekehrt():
    oe = R.only_empty_summary(D)
    assert oe["mean_only_empty"] == pytest.approx(0.044722222222222226, rel=1e-9)
    assert oe["max_only_empty"] == pytest.approx(0.375)
    assert oe["max_only_empty_cell"]["width"] == pytest.approx(0.5)
    assert oe["max_only_empty_cell"]["level"] == "leicht" and oe["max_only_empty_cell"]["n_ulds"] == 8
    assert oe["mean_only_full"] == 0.0
    assert all(c["only_full_bad_rate"] == 0.0 for c in R.cells(D))


def test_befund_cp_sat_immer_optimal():
    assert all(c["exact_optimal_rate"] == 1.0 for c in R.cells(D))
