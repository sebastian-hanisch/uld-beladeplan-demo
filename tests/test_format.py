"""Tests für uldb_format.py: deutsches Dezimalkomma, Vorzeichen."""
from uldb_format import fmt_num, fmt_pct, fmt_pp


def test_fmt_num_verwendet_komma():
    assert fmt_num(74.5, 1) == "74,5"
    assert fmt_num(0.0, 1) == "0,0"


def test_fmt_num_signed_zeigt_plus():
    assert fmt_num(3.2, 1, signed=True) == "+3,2"
    assert fmt_num(-3.2, 1, signed=True) == "-3,2"


def test_fmt_pct_multipliziert_mit_hundert():
    assert fmt_pct(0.688, 1) == "68,8 %"
    assert fmt_pct(0.0, 1) == "0,0 %"


def test_fmt_pp_hat_vorzeichen_per_default():
    assert fmt_pp(2.4) == "+2,4 Prozentpunkte"
    assert fmt_pp(-1.5) == "-1,5 Prozentpunkte"
