# 🛫 Beladeplan: welche ULDs, welche Position?

**[→ Demo live ausprobieren](https://sebastianhanisch-uld-beladeplan-demo.streamlit.app/)**

Zweites Stück der Packen-Ausbaulinie, eigenständig neben [`uld-gewicht-demo`](https://github.com/sebastian-hanisch/uld-gewicht-demo)
(dort: Volumen-Packung **eines** ULD gegen dessen eigenen Schwerpunkt) und geschärft gegenüber
[`stauplanung-demo`](https://github.com/sebastian-hanisch/stauplanung-demo) (dort: Vollbelegung + Umstau-Sequenz an **einem**
Zeitpunkt): welche ULDs kommen auf welche der 10 Laderaumpositionen eines Flugzeugs, damit keine Position ihre Gewichtsgrenze
überschreitet und der Flugzeug-**Schwerpunkt** sowohl mit **vollem** als auch mit **leerem** Tank im zulässigen Fenster liegt -
bei maximal geladenem Gewicht? Die Demo zeigt live **eine Instanz** mit drei Verfahren (H_greedy, ignoriert Balance;
H_balance, schwerpunkt-bewusst; CP-SAT, das bewiesene Optimum, hier immer mitgerechnet) und vorgerechnet die Messreihe über
**80 Instanzen je Zelle** (45 Zellen), die die Aussage trägt.

## Warum dieses Problem

Bei Luftfracht gilt eine reale Vorschrift (Weight & Balance): der Schwerpunkt des beladenen Flugzeugs muss in einem
zulässigen Fenster um eine Referenzlage liegen, und zwar **während des gesamten Flugs** - nicht nur beim Start. Das Modell
hier bildet zwei Zeitpunkte ab: vollem Tank (Start) und leerem Tank (nach Verbrauch). `stauplanung-demo` prüft eine
vergleichbare Schwerpunktgrenze nur an einem Zeitpunkt (dem Stau-Zeitpunkt) und belegt dabei **alle** Container - eine
Sequenz-/Umstau-Aufgabe. Dieses Stück ist bewusst ein **Auswahlproblem**: nicht jedes ULD muss/kann mitfliegen (das Ziel ist,
das geladene Gewicht zu maximieren), es gibt keine Sequenz-/Umstau-Dimension (eine einmalige Zuordnung), und das Fenster muss
an **zwei** Zeitpunkten gleichzeitig halten - ein Unterschied, der sich messbar auswirkt (siehe Befund 4 unten), nicht nur
behauptet ist.

## Modell

- **Flugzeug:** Leergewicht 40.000 kg bei Hebelarm 17,0 m (Referenzpunkt), Treibstoff 8.000 kg (Hebelarm 17,0 m, selbst
  neutral), Schwerpunktfenster [17,0 − Breite; 17,0 + Breite] m, Breite als Regler (0,08 bis 1,0 m).
- **10 Laderaumpositionen**, gleichmäßig von Hebelarm 6,0 bis 28,0 m, je 2.200 kg Gewichtsgrenze.
- **ULDs:** 8/12/16 Stück je Instanz, Gewicht gleichverteilt in einem von drei Bereichen (leicht 200-1.200 kg, gemischt
  200-2.200 kg, schwer 1.200-2.200 kg).
- **Zielgröße:** maximiere das geladene Gesamtgewicht, unter Positions-Gewichtsgrenze und dem Schwerpunktfenster **an beiden
  Zeitpunkten** (voller und leerer Tank - Treibstoffverbrauch ändert nur das Gesamtgewicht, nicht den Hebelarm des Tanks
  selbst in diesem Modell).
- **H_greedy:** schwerste ULDs zuerst, jeweils die erste freie Position mit ausreichender Gewichtsgrenze (Positions-Reihenfolge
  von vorn nach hinten) - bildet nach, wer ohne Rücksicht auf Balance lädt.
- **H_balance:** schwerste ULDs zuerst, aber jeweils die freie Position, die den Schwerpunkt (Leergewicht-Zustand) am
  nächsten an die Fenstermitte bringt.
- **Reparatur:** entfernt aus einer unzulässigen Zuordnung so lange das ULD mit dem größten gewichteten Hebelabstand zur
  Fenstermitte, bis beide Zeitpunkte zulässig sind - bildet nach, was ein Lademeister tut, wenn ein Plan die Grenze reißt.
- **Exakt (CP-SAT):** 0/1-Zuordnung ULD→Position, Schwerpunktfenster an beiden Zeitpunkten linearisiert, maximiertes
  geladenes Gewicht; wird bei dieser Instanzgröße (10 Positionen, bis 16 ULDs) **immer live gerechnet**, kein separater
  Exakt-Tab - fand in 100 % der 3.600 gemessenen Instanzen die bewiesen optimale Lösung innerhalb von 2 s.

Flugzeug- und Positionsdaten erfunden, nicht kalibriert; die Größenordnung (Hebelarme 6-28 m, Fensterbreite 0,08-1,0 m)
orientiert sich grob an schmalen Verkehrsflugzeugen, ist aber kein Zitat einer echten Gewichts-und-Schwerpunkt-Tabelle. Nur
der Längs-Schwerpunkt (fore/aft) - keine Seitenlage, die `stauplanung-demo` mit "Seitenneigung" bereits hat, hier bewusst
nicht übernommen, um die Abgrenzung klar zu halten.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen aus `data/uldb_results.json` (45 Zellen × 80 Instanzen, aus `packen-planung/messreihe_uld_beladeplan/sweep_data.json`,
bitgleich übernommen), nachgerechnet in `tests/test_claims.py`.

| Frage | Befund |
|---|---|
| Verletzt eine Regel ohne Balance-Bewusstsein das Schwerpunktfenster? | Ja, oft: ±0,5 m, gemischte Gewichte, 12 ULDs - **68,8 %** der Instanzen verletzt; bei ±0,3 m sogar **100 %**. |
| Was kostet das an Ladegewicht? | Viel, und mehr bei engerem Fenster: bei ±0,5 m im Mittel **10,3 %** weniger geladenes Gewicht als das CP-SAT-Optimum (nach Reparatur), bei ±0,08 m **43,6 %**, im Extremfall (gemischt, 8 ULDs, ±0,08 m) **55,3 %**. |
| Reicht H_balance, um das auszugleichen? | Fast immer: in **42 von 45** gemessenen Zellen liegt die Lücke von H_balance (repariert) zum CP-SAT-Optimum bei exakt **0,0 %**. |
| Ist H_balance eine bewiesen optimale Regel? | **Nein** - bei sehr engem Fenster (±0,08 m) öffnet sich eine kleine, aber echte Lücke, bis **2,4 %** (gemischte Gewichte, 12 ULDs); das wurde absichtlich stressgetestet, bevor es als Befund galt (siehe unten). |
| Fängt der Zwei-Zeitpunkte-Check echte Fälle? | Ja: über alle 45 Zellen verletzt H_greedy (unrepariert) **nie** nur den vollen Tank (0,0 % in jeder einzelnen Zelle), aber im Mittel **4,5 %** und im Extremfall (±0,5 m, leicht, 8 ULDs) bis **37,5 %** der Instanzen **nur** den leeren Tank. |
| Ist CP-SAT verlässlich exakt? | Ja: in allen 3.600 gerechneten Instanzen fand der Solver die bewiesen optimale Lösung (Status OPTIMAL) innerhalb von 2 s. |

**Warum "H_balance fast immer optimal" erst stressgetestet wurde, bevor es als Befund galt:** eine Kennzahl, die über 42 von
45 Zellen exakt 0,0 % ist, ist ein Nullspalten-Verdacht, kein automatischer Erfolg (siehe DEMO-PLAYBOOK Abschnitt 4/8). Die
Vorab-Messreihe (`packen-planung/messreihe_uld_beladeplan/ERGEBNIS.md`) hat deshalb gezielt sehr enge Fenster (0,08/0,15 m,
zusätzlich zu den drei realistischeren Breiten) und einen Stresstest mit nur 4 Positionen gerechnet - beide zeigen echte,
messbare Lücken, die den Nullbefund als real bestätigen, statt ihn zu verschleiern.

**Warum "nur voll verletzt" nie vorkommt:** kein Messzufall, sondern eine Modelleigenschaft. Weil der Treibstoff neutral ist
(derselbe Hebelarm wie das Leergewicht), liegt der Schwerpunkt-Index ohne Ladung an beiden Zeitpunkten exakt auf der
Fenstermitte; das Gesamtgewicht ist am leeren Tank immer kleiner, jede Momentabweichung durch die Ladung wirkt sich dort
also mindestens so stark aus wie am vollen Tank. Bewiesen in `tests/test_model.py::test_nur_voll_verletzt_ist_strukturell_unmoeglich`
und empirisch bestätigt (`only_full_bad_rate` ist in jeder der 45 Zellen exakt 0,0).

## Ehrliche Grenzen

- **Nur der Längs-Schwerpunkt** (fore/aft) - keine Seitenlage (links/rechts), die `stauplanung-demo` mit "Seitenneigung"
  bereits hat.
- **H_balance ist keine bewiesen optimale Regel** - bei sehr engem Fenster reicht sie nicht aus; eine dritte, komplexere
  Heuristik (z. B. eine Tauschregel) wäre eine Ausbauidee, ist hier bewusst nicht umgesetzt.
- **Positions-Gewichtsgrenzen sind unabhängig voneinander** - reale Frachträume haben oft zusätzliche Grenzen für
  benachbarte Positionen zusammen (nicht modelliert).
- **Treibstoff hat denselben Hebelarm wie das Leergewicht** (neutral) - ein asymmetrischer Tank-Arm wäre eine mögliche
  Verschärfung, hier bewusst nicht umgesetzt (siehe Befund "warum nur voll verletzt nie vorkommt" oben - mit
  asymmetrischem Tank-Arm würde diese strukturelle Garantie entfallen).
- **Flugzeug- und Positionsdaten erfunden, nicht kalibriert.**

## Befunde und Korrekturen gegenüber dem Plan

Der freigegebene Detailplan (`packen-planung/plan_uld_beladeplan.py`) sah für das Preset "Viele ULDs, wenige Positionen" als
Abnahmekriterium vor: "n_loaded (CP-SAT) < 16 in fast allen Instanzen (Positionsgrenze bindet)". Die Messreihe speichert
`n_loaded` nicht je Zelle - aber die Prüfung braucht auch keine Messung: mit nur 10 Positionen und der Nebenbedingung
"höchstens ein ULD je Position" (`uldb_oracle.solve_exact`) kann CP-SAT bei 16 ULDs **nie** mehr als 10 laden, unabhängig
vom Zufall. `uldb_stories.check_viele_ulds_wenige_positionen` prüft deshalb strukturell (`n_ulds > N_POS`) statt statistisch
- eine Verschärfung des Kriteriums von "fast immer" auf "immer", keine Abschwächung.

**Beim Bauen gefunden (AP 7, Verifikation):** `tests/test_frozen_reference.py` schlug anfangs sporadisch fehl (ca. 1 von 5-7
vollen Testläufen), aber ausschließlich beim `cg_full`/`cg_empty`-Vergleich des CP-SAT-Ergebnisses, nie bei H_greedy/H_balance
und nie bei `cargo_weight` selbst. Ursache: alle 10 Positionen haben dieselbe Gewichtsgrenze (2.200 kg), daher erreichen bei
manchen Instanzen mehrere unterschiedliche Zuordnungen exakt dasselbe optimale Ladegewicht - und CP-SAT mit einzelnem
Zielterm (`model.Maximize(sum(...))`, `num_search_workers=8`) löst solche Gleichstände nicht deterministisch auf (siehe
DEMO-PLAYBOOK Abschnitt 4). Behoben, indem der eingefrorene Vergleich für das CP-SAT-Ergebnis NUR noch `cargo_weight`,
`n_loaded`, `feasible` und den Solver-Status prüft - nicht mehr die konkrete Zuordnung (`cg_full`/`cg_empty`), die von der
zufällig gefundenen Optimallösung abhängt. H_greedy/H_balance bleiben weiter bitgenau geprüft (reine Python-Verfahren ohne
Gleichstand-Mehrdeutigkeit in der Zuordnung selbst).

## Tests

Testanzahl und Laufzeit siehe Ausgabe von `_venvs/test/Scripts/python.exe -m pytest tests -v`:

- `tests/test_model.py` - die 13 Korrektheits-Checks aus `messreihe_uld_beladeplan/check.py` (Handrechnung, Grenzfälle von
  `cg_ok()`, CP-SAT gegen eine unabhängige Brute-Force-Referenz, CP-SAT nie schlechter als eine reparierte Heuristik,
  `repair_to_feasible()` immer zulässig, der PFLICHT-Regressionstest für den geschärften Hook, Determinismus), plus den
  PFLICHT-Zwei-Zeitpunkte-Regressionstest (eine konstruierte Instanz, bei der die Zuordnung am vollen Tank zulässig, am
  leeren Tank aber unzulässig ist) und den strukturellen Beleg, warum die umgekehrte Richtung in diesem Modell nicht
  vorkommen kann.
- `tests/test_frozen_reference.py` - vier eingefrorene ULD-Gewichtslisten (feste Zahlenwerte, keine Zufallsziehung zur
  Testzeit), CI-robust gegen NumPy-Versionsdrift.
- `tests/test_results.py`, `tests/test_format.py` - Zell-Zuordnung (AP 0: alle 45 Reglerkombinationen liegen exakt auf
  einer gemessenen Zelle), Urteilslogik in drei Zuständen, Zahlenformate.
- `tests/test_visualization.py`, `tests/test_pdf_export.py` - Plotly-Figuren und PDF-Export bauen ohne Fehler.
- `tests/test_presets.py`, `tests/test_stories.py` - Permalink-Parsing, alle fünf Presets bestehen ihre Abnahmekriterien
  gegen die Messreihe.
- `tests/test_claims.py` - jede Zahl aus dem README-Abschnitt "Befunde" gegen `data/uldb_results.json` nachgerechnet.
- `tests/test_app.py` - AppTest: Skelett, Footer, jedes Preset, Permalink, alle Regler an Min/Max, alle drei
  Urteilszustände, keine wirkungslosen Regler, PDF-Download, keine toten Datei-Links.

Zusätzlich: `tools/mutation_check.py` (Fehler-Einbau-Test für `uldb_model.py`/`uldb_heuristics.py`, siehe
`tools/mutants.py` für die Einordnung gleichwertiger Überlebender) und `tools/check_full.py` (volles Bau-Gate: Wiederholung
der Messreihe gegen `data/uldb_results.json` - hier **bitgleich** möglich, weil die Zellen-Seeds über `zlib.crc32` statt
Pythons prozess-gesalzenem `hash()` erzeugt werden, siehe `tools/sweep.py`).

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Einstiegspunkt |
| `uldb_constants.py` | Flugzeug/Positionen, Reglerstufen, Presets, Farben |
| `uldb_presets.py` | Reglerspezifikation, Permalink, Presets, Seed-Knopf |
| `uldb_model.py` | Datentypen (Position, ULD, Aircraft), Schwerpunkt-Kennzahlen, `evaluate_assignment` (aus `beladeplan.py` übernommen) |
| `uldb_heuristics.py` | H_greedy, H_balance, Reparatur (aus `beladeplan.py` übernommen) |
| `uldb_oracle.py` | CP-SAT-Exakt (lazy `ortools`-Import, aus `beladeplan.py` übernommen) |
| `uldb_results.py` | Laden und Auswerten von `data/uldb_results.json`, Urteilslogik |
| `uldb_format.py` | Zahlenformate mit deutschem Dezimalkomma |
| `uldb_visualization.py` | Laderaumkarte (drei Zuordnungen), Lücke-über-Fensterbreite-, Regime-Grafik |
| `uldb_stories.py` | Abnahmekriterien der Presets |
| `uldb_pdf_export.py` | Beladeplan-PDF |
| `tools/sweep.py` | Reproduktion der Messreihe (nicht in CI) |
| `tools/check_full.py` | Volles Bau-Gate (bitgleicher Vergleich) |
| `tools/mutants.py`, `tools/mutation_check.py` | Fehler-Einbau-Test der Kernmodule |
| `data/uldb_results.json` | Messreihe: 45 Zellen × 80 Instanzen |
| `tests/` | Testsuite |

## Bewusst nicht umgesetzt

Seitenlage/Seitenneigung, gruppierte Positions-Gewichtsgrenzen (Positionsgruppen mit gemeinsamer Grenze), ein
asymmetrischer Treibstoff-Hebelarm, eine dritte (Tausch-)Heuristik, mehr als 10 Positionen oder 16 ULDs, echte
Flugzeugtyp-Daten, ein separater Exakt-Tab (CP-SAT läuft hier immer live).

## Lokal ausführen

```
pip install -r requirements-dev.txt
streamlit run app.py
```

---

Gebaut mit Streamlit, Plotly, NumPy, OR-Tools und fpdf2.

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zum Thema: [Luftfracht optimieren](https://sebastianhanisch.net/luftfracht-optimierung.html).
