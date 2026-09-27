"""Tests für uldb_presets.py: Permalink-Parsing, Einrasten auf Stufen, Presets."""
import uldb_constants as C
import uldb_presets as P


def test_alle_presets_haben_gueltige_werte():
    for name, p in C.PRESETS.items():
        assert p["width"] in C.WIDTH_OPTIONS
        assert p["level"] in C.LEVEL_OPTIONS
        assert p["n_ulds"] in C.ULDS_OPTIONS
        assert C.SEED_RANGE[0] <= p["seed"] <= C.SEED_RANGE[1]


def test_parse_setting_rastet_zahl_auf_naechste_stufe_ein():
    spec = P.SETTING_SPECS["width_slider"]
    assert P.parse_setting(spec, "0.09") == 0.08
    assert P.parse_setting(spec, "0.4") == 0.5


def test_parse_setting_text_nur_bei_exaktem_treffer():
    spec = P.SETTING_SPECS["level_select"]
    assert P.parse_setting(spec, "schwer") == "schwer"
    assert P.parse_setting(spec, "sehr_schwer") is None


def test_parse_setting_seed_wird_begrenzt():
    spec = P.SETTING_SPECS["seed_input"]
    assert P.parse_setting(spec, "500") == C.SEED_RANGE[1]
    assert P.parse_setting(spec, "-5") == C.SEED_RANGE[0]


def test_parse_setting_ungueltige_zahl_gibt_none():
    spec = P.SETTING_SPECS["width_slider"]
    assert P.parse_setting(spec, "abc") is None
    assert P.parse_setting(spec, "nan") is None
    assert P.parse_setting(spec, "inf") is None


def test_bounds_liefert_lo_hi_fuer_seed():
    lo, hi = P.bounds("seed_input")
    assert (lo, hi) == C.SEED_RANGE
