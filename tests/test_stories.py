"""Tests für uldb_stories.py: jedes Preset gegen die vorgerechnete Messreihe, einzeln prüfbar."""
import uldb_results as R
import uldb_stories as S

D = R.load_results()


def test_alle_presets_bestehen_ihre_abnahmekriterien():
    results = S.check_all(D)
    failed = [(name, msg) for name, (ok, msg) in results.items() if not ok]
    assert not failed, failed


def test_check_all_deckt_alle_fuenf_presets_ab():
    assert set(S.check_all(D)) == set(S.CHECKS) == {
        "Standard", "Enges Fenster", "Weites Fenster", "Viele ULDs, wenige Positionen", "Extremfall"
    }
