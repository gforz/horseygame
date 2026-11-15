"""names.py — The pool of race horse names.

Names are drawn from horse_names.txt in a shuffled cycle, so a name is not
reused until the whole file has been handed out.
"""

import random
from pathlib import Path

from game import constants as C

NAMES_FILE = Path(__file__).parents[1] / "horse_names.txt"

_unused_race_names: list[str] = []


def load_horse_names() -> list[str]:
    """Load the available race names from the adjacent text file."""
    names_path = NAMES_FILE
    with names_path.open(encoding="utf-8") as names_file:
        names = [line.strip() for line in names_file if line.strip()]
    if len(names) != len(set(names)):
        raise ValueError(f"{names_path.name} must not contain duplicate horse names")
    if len(names) < C.LANE_COUNT:
        raise ValueError(
            f"{names_path.name} must contain at least {C.LANE_COUNT} horse names"
        )
    return names


def draw_race_names() -> list[str]:
    """Draw unique names, exhausting a shuffled name cycle before refilling."""
    global _unused_race_names

    names = []
    skipped = []
    while len(names) < C.LANE_COUNT:
        if not _unused_race_names:
            _unused_race_names = load_horse_names()
            random.shuffle(_unused_race_names)

        name = _unused_race_names.pop()
        if name in names:
            skipped.append(name)
        else:
            names.append(name)

    _unused_race_names.extend(skipped)
    return names