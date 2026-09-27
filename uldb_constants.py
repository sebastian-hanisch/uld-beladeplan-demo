"""Beladeplan über mehrere ULD-Positionen - feste Annahmen, Reglerstufen, Presets, Farben.

Flugzeug- und Positionsdaten erfunden, nicht kalibriert (siehe packen-planung/messreihe_uld_beladeplan/ERGEBNIS.md,
Abschnitt "Vorbehalte"). Nur der Längs-Schwerpunkt (fore/aft); keine Seitenlage - bewusst nicht übernommen,
um die Abgrenzung zu stauplanung-demo klar zu halten."""
from uldb_model import Aircraft, Position

# --- Flugzeug und Positionen (siehe ERGEBNIS.md "Modell") --------------------------------------------------
N_POS = 10
ARM_MIN, ARM_MAX = 6.0, 28.0
POS_MAX_WEIGHT_KG = 2200.0
CENTER_M = (ARM_MIN + ARM_MAX) / 2.0  # 17.0

EMPTY_WEIGHT_KG = 40000.0
FUEL_KG = 8000.0

POSITIONS = [Position(f"p{i}", ARM_MIN + i * (ARM_MAX - ARM_MIN) / (N_POS - 1), POS_MAX_WEIGHT_KG) for i in range(N_POS)]
POS_BY_NAME = {p.name: p for p in POSITIONS}


def make_aircraft(width_m: float) -> Aircraft:
    """Treibstoff hat denselben Hebelarm wie das Leergewicht (neutral) - siehe ERGEBNIS.md "Vorbehalte"."""
    return Aircraft(
        empty_weight_kg=EMPTY_WEIGHT_KG, empty_moment_kgm=EMPTY_WEIGHT_KG * CENTER_M,
        fuel_kg=FUEL_KG, fuel_arm_m=CENTER_M,
        cg_min_m=CENTER_M - width_m, cg_max_m=CENTER_M + width_m,
    )


# --- Reglerstufen (genau die drei Sweep-Dimensionen, siehe AP 0 / tests/test_results.py) ---------------------
WIDTH_OPTIONS = (1.0, 0.5, 0.3, 0.15, 0.08)
WIDTH_DEFAULT = 0.5

ULDS_OPTIONS = (8, 12, 16)
ULDS_DEFAULT = 12

WEIGHT_LEVELS = {"leicht": (200.0, 1200.0), "gemischt": (200.0, 2200.0), "schwer": (1200.0, 2200.0)}
LEVEL_OPTIONS = ("leicht", "gemischt", "schwer")
LEVEL_DEFAULT = "gemischt"
LEVEL_LABEL = {"leicht": "leicht (200-1.200 kg)", "gemischt": "gemischt (200-2.200 kg)", "schwer": "schwer (1.200-2.200 kg)"}

SEED_RANGE = (0, 79)  # N_INSTANCES der Messreihe (80 Instanzen je Zelle)
SEED_DEFAULT = 0

COLOR_GREEDY = "#2a6fb0"
COLOR_BALANCE = "#9fc2e6"
COLOR_EXACT = "#3d8b5f"

PRESETS = {
    "Standard": dict(width=0.5, level="gemischt", n_ulds=12, seed=0),
    "Enges Fenster": dict(width=0.08, level="gemischt", n_ulds=12, seed=0),
    "Weites Fenster": dict(width=1.0, level="leicht", n_ulds=8, seed=0),
    "Viele ULDs, wenige Positionen": dict(width=0.3, level="gemischt", n_ulds=16, seed=0),
    "Extremfall": dict(width=0.08, level="gemischt", n_ulds=8, seed=0),
}

PRESET_HELP = {
    "Standard": "Fensterbreite ±0,5 m, gemischte Gewichte, 12 ULDs: eine Regel ohne Balance-Bewusstsein verletzt das Fenster oft und verschenkt Ladegewicht.",
    "Enges Fenster": "Fensterbreite ±0,08 m: hier zeigt sich die Grenze der balance-bewussten Regel.",
    "Weites Fenster": "Fensterbreite ±1,0 m, leichte Gewichte, 8 ULDs: der Unterschied zwischen den Regeln verschwindet fast.",
    "Viele ULDs, wenige Positionen": "16 ULDs, nur 10 Positionen, ±0,3 m: das Auswahlproblem wird sichtbar - nicht alle ULDs können mitfliegen.",
    "Extremfall": "Fensterbreite ±0,08 m, gemischte Gewichte, 8 ULDs: größter gemessener wirtschaftlicher Preis der naiven Regel.",
}
