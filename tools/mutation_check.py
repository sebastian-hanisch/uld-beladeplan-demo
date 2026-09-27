"""Fehler-Einbau-Test für die beiden Kernmodule (uldb_model.py, uldb_heuristics.py): baut einzeln einen
Fehler ein und prüft, ob die Tests ihn finden.

Aufruf (im Projektordner): _venvs/test/Scripts/python.exe tools/mutation_check.py [Teilstring des Dateinamens] [--jobs N]
Für ein reproduzierbares Ergebnis --jobs 1 verwenden (langsamer): bei starker Parallelität (Standard 4, hier
schon ab 6 beobachtet) können mehrere gleichzeitige CP-SAT-Läufe (je `num_search_workers=8` in
uldb_oracle.py) unter CPU-Konkurrenz das Zeitlimit knapper ausschöpfen und dadurch vereinzelt andere
Überlebende melden - siehe tools/mutants.py EQUIVALENT_NOTES für den beobachteten Effekt.
Jeder Mutant ersetzt genau eine Stelle; Überlebende sind entweder gleichwertig (kein sichtbarer Unterschied)
oder eine Lücke der Tests. Jeder Mutant läuft in einer eigenen temporären Kopie (deshalb parallel möglich,
Standard 4 Jobs); PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Überlebenden vortäuscht;
Quelltexte als LF (Windows-Python schreibt sonst CRLF und die Zeichenketten in tools/mutants.py finden nichts).

Selbstprüfung (Baseline): VOR den Mutanten läuft eine UNVERÄNDERTE Kopie gegen die Tests. Besteht sie nicht,
bricht das Werkzeug ab - sonst wäre jeder "gefundene" Mutant vorgetäuscht.

Die Mutanten sind handverlesen (siehe tools/mutants.py) - bei nur zwei kleinen, mechanisch aus beladeplan.py
übernommenen Kernmodulen deckt eine handverlesene Liste jede Vergleichsoperation, jede Vorzeichen-/
Faktor-Stelle und jede Sortierordnung ab. Die relevanten Tests laufen auf eingefrorenen Instanzen
(tests/data/uldb_frozen.json) oder auf Zufallsinstanzen mit festem Seed (kein Mutant hängt vom
Zufallsgenerator selbst ab, nur von der NumPy-Ziehung bei festem Seed - siehe DEMO-PLAYBOOK Abschnitt 4)."""
import concurrent.futures as cf
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mutants import MUTANTS  # noqa: E402

PY = sys.executable
TIMEOUT = 180
CORE_TESTS = ["test_model.py", "test_frozen_reference.py"]


def make_copy(work: pathlib.Path):
    for f in ROOT.glob("*.py"):
        (work / f.name).write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    (work / "tests").mkdir()
    for f in (ROOT / "tests").glob("*.py"):
        (work / "tests" / f.name).write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    (work / "tests" / "data").mkdir()
    for f in (ROOT / "tests" / "data").glob("*"):
        shutil.copy(f, work / "tests" / "data" / f.name)
    (work / "data").mkdir()
    for f in (ROOT / "data").glob("*"):
        shutil.copy(f, work / "data" / f.name)


def run_one(n, name, old, new, tmp_root):
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"uldb_mut{n}_", dir=tmp_root))
    try:
        make_copy(work)
        path = work / name
        original = path.read_bytes().decode("utf-8")
        if original.count(old) != 1:
            return n, name, old, new, f"FEHLER:{original.count(old)}"
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        args = [PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"] + [f"tests/{t}" for t in CORE_TESTS]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            r = subprocess.run(args, cwd=work, env=env, capture_output=True, text=True, timeout=TIMEOUT)
            return n, name, old, new, "UEBERLEBT" if r.returncode == 0 else "gefunden"
        except subprocess.TimeoutExpired:
            return n, name, old, new, "gefunden(Zeitüberschreitung)"
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    jobs = 4
    for i, a in enumerate(sys.argv[1:]):
        if a == "--jobs":
            jobs = int(sys.argv[i + 2])
            args = [x for x in args if x != sys.argv[i + 2]]
    only = args[0] if args else ""
    tmp_root = tempfile.mkdtemp(prefix="uldb_mut_")
    status = run_one(0, "uldb_model.py", "from __future__ import annotations",
                      "from __future__ import annotations", tmp_root)[4]
    if status != "UEBERLEBT":
        print(f"ABBRUCH: unveränderte Kopie besteht die Tests nicht ({status}) - Ergebnisse wären wertlos")
        shutil.rmtree(tmp_root, ignore_errors=True)
        return 2
    print("Selbstprüfung: unveränderte Kopie besteht alle Tests (Werkzeug funktioniert)", flush=True)
    todo = [(n, *m) for n, m in enumerate(MUTANTS, 1) if not only or only in m[0]]
    survivors, errors, killed = [], [], 0
    with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(run_one, n, name, old, new, tmp_root) for n, name, old, new in todo]
        for fut in cf.as_completed(futures):
            n, name, old, new, res_status = fut.result()
            if res_status.startswith("FEHLER"):
                errors.append((n, name, old[:60], res_status))
                print(f"[{n:3d}] FEHLER (Stelle nicht eindeutig: {res_status})  {name}: {old[:60]!r}", flush=True)
            elif res_status == "UEBERLEBT":
                survivors.append((n, name, old[:70], new[:70]))
                print(f"[{n:3d}] UEBERLEBT  {name}: {old[:80]!r} -> {new[:80]!r}", flush=True)
            else:
                killed += 1
                print(f"[{n:3d}] {res_status}  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} überlebt, {len(errors)} Fehler in der Mutantenliste (von {len(todo)})")
    shutil.rmtree(tmp_root, ignore_errors=True)
    return 1 if (survivors or errors) else 0


if __name__ == "__main__":
    sys.exit(main())
