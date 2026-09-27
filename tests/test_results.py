"""Tests für uldb_results.py: exakte Zell-Zuordnung (AP 0), Urteilslogik in drei Zuständen, Kennzahlen."""
from __future__ import annotations

from itertools import product

import pytest

import uldb_results as R

D = R.load_results()


def test_alle_reglerkombinationen_liegen_auf_einer_gemessenen_zelle():
    """AP 0: die drei Regler (Fensterbreite, Gewichtsniveau, ULD-Zahl) bilden zusammen genau die drei
    Sweep-Dimensionen ab - 5 x 3 x 3 = 45 Kombinationen, keine Näherung nötig."""
    combos = list(product(R.WIDTH_OPTIONS, R.LEVEL_OPTIONS, R.ULDS_OPTIONS))
    assert len(combos) == 45
    for width, level, n_ulds in combos:
        cell = R.find_cell(D, width, level, n_ulds)
        assert cell["level"] == level and cell["n_ulds"] == n_ulds
        assert abs(cell["width"] - width) < 1e-9


def test_unbekannte_kombination_wirft_key_error():
    with pytest.raises(KeyError):
        R.find_cell(D, 0.2, "gemischt", 12)


def test_45_zellen_insgesamt_ohne_duplikate():
    seen = set()
    for c in R.cells(D):
        key = (c["width"], c["level"], c["n_ulds"])
        assert key not in seen
        seen.add(key)
    assert len(seen) == 45


@pytest.mark.parametrize("args,expected_state", [
    ((0.5, "gemischt", 12), R.STATE_OPTIMAL),
    ((0.08, "gemischt", 12), R.STATE_LUECKE),
    ((1.0, "leicht", 8), R.STATE_UNKRITISCH),
])
def test_presets_liefern_das_im_plan_beschriebene_urteil(args, expected_state):
    cell = R.find_cell(D, *args)
    assert R.judgment(cell) == expected_state


def test_alle_drei_urteilszustaende_kommen_in_der_messreihe_vor():
    """Kein Zustand ist ein toter Zweig (Nullspalten-Signal): jeder der drei Zustände muss unter den 45
    Zellen mindestens einmal auftreten, sonst wäre die App-Meldung nie in diesem Zustand zu sehen."""
    states = {R.judgment(c) for c in R.cells(D)}
    assert states == {R.STATE_UNKRITISCH, R.STATE_OPTIMAL, R.STATE_LUECKE}


def test_regime_rows_deckt_alle_45_zellen_ab():
    rows = R.regime_rows(D)
    assert len(rows) == 45
    for row in rows:
        assert row["state"] in R.STATE_LABEL
        assert row["label"] == R.STATE_LABEL[row["state"]]


def test_width_rows_liefert_alle_fuenf_fensterbreiten_derselben_zelle():
    rows = R.width_rows(D, "gemischt", 12)
    assert [r["width"] for r in rows] == list(R.WIDTH_OPTIONS)
    assert all(r["level"] == "gemischt" and r["n_ulds"] == 12 for r in rows)


def test_only_empty_summary_only_full_ist_immer_null():
    """ERGEBNIS.md Befund 4 / tests/test_model.py::test_nur_voll_verletzt_ist_strukturell_unmoeglich:
    only_full_bad_rate ist in JEDER Zelle exakt 0,0 - strukturell, nicht nur gemessen."""
    s = R.only_empty_summary(D)
    assert s["mean_only_full"] == 0.0
    assert s["mean_only_empty"] > 0.0  # der Zwei-Zeitpunkte-Effekt ist real, kein toter Zweig
    assert 0.0 < s["max_only_empty"] <= 1.0


def test_gap_balance_summary_hat_nur_wenige_zellen_mit_echter_luecke():
    """Nullspalten-Signal umgekehrt: gap_balance_pct ist in den MEISTEN Zellen exakt 0,0 - das ist selbst
    stressgetestet worden (ERGEBNIS.md Befund 3), nicht einfach als Erfolg hingenommen."""
    s = R.gap_balance_summary(D)
    assert s["n_total"] == 45
    assert 0 < s["n_total"] - s["n_zero"] < s["n_total"]  # weder "nie" noch "immer" eine Lücke
    assert s["max_gap"] > 0.0


def test_max_gap_greedy_liegt_bei_sehr_engem_fenster():
    cell = R.max_gap_greedy(D)
    assert cell["width"] == 0.08


def test_judgment_text_enthaelt_die_gemessenen_prozentzahlen():
    cell = R.find_cell(D, 0.5, "gemischt", 12)
    text = R.judgment_text(cell)
    assert "68,8" in text  # violation_rate_greedy_raw 0.6875 -> "68,8 %"
    assert R.STATE_LABEL[R.STATE_OPTIMAL] in text
