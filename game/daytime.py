"""daytime.py — The time of day, shared by every scene.

The day has 4 stages. Each horse race moves the day on one stage, and
sleeping (only possible at noon or night) moves it on two.
"""

STAGES = ["Morning", "Midday", "Noon", "Night"]

stage = 0   # index into STAGES; the game starts in the morning


def name() -> str:
    """Name of the current stage, e.g. "Noon"."""
    return STAGES[stage]


def is_night() -> bool:
    """The track is empty and the shop and Glue are closed at night."""
    return STAGES[stage] == "Night"


def can_sleep() -> bool:
    """You can only sleep at noon or at night."""
    return STAGES[stage] in ("Noon", "Night")


def advance(count: int = 1) -> None:
    """Move the day on by `count` stages, wrapping around after night."""
    global stage
    stage = (stage + count) % len(STAGES)