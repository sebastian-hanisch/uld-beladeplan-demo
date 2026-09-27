"""Volles Bau-Gate (AP 7): wiederholt den Sweep (tools/sweep.py) und vergleicht das Ergebnis MIT der
eingecheckten data/uldb_results.json auf BITGLEICHHEIT.

Anders als bei uld-gewicht-demo (dort `hash()` auf Strings, pro Prozess zufällig gesalzen, siehe
uld-gewicht-demo/tools/check_full.py) verwendet dieser Sweep `zlib.crc32` für die Zellen-Seeds (siehe
tools/sweep.py) - das ist über Prozesse und Python-Versionen hinweg stabil. Eine bitgleiche Reproduktion ist
hier deshalb tatsächlich zu erwarten, nicht nur eine statistische Näherung.

Aufruf (im Projektordner): _venvs/runtime/Scripts/python.exe tools/check_full.py
(Laufzeit rund 70-90 s, siehe tools/sweep.py - deshalb nicht Teil der CI.)"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from sweep import run_sweep  # noqa: E402


def main():
    checked = ROOT / "data" / "uldb_results.json"
    expected = json.loads(checked.read_text(encoding="utf-8"))

    out = run_sweep()

    top_mismatches = [(k, out.get(k), expected[k]) for k in expected if k != "rows" and out.get(k) != expected[k]]
    row_mismatches = []
    if len(out.get("rows", [])) == len(expected["rows"]):
        for i, (got, exp) in enumerate(zip(out["rows"], expected["rows"])):
            if got != exp:
                row_mismatches.append((i, got, exp))
    else:
        row_mismatches.append(("Anzahl Zeilen", len(out.get("rows", [])), len(expected["rows"])))

    ok = not top_mismatches and not row_mismatches
    print(f"Kopfdaten: {'bitgleich' if not top_mismatches else f'{len(top_mismatches)} Abweichungen'}")
    for m in top_mismatches:
        print("   ", m)
    print(f"Zeilen (45 Zellen): {'bitgleich' if not row_mismatches else f'{len(row_mismatches)} Abweichungen'}")
    for m in row_mismatches[:5]:
        print("   ", m)
    print()
    print("BAU-GATE BESTANDEN (bitgleich)" if ok else "BAU-GATE FEHLGESCHLAGEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
