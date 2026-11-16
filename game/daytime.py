"""daytime.py — The time of day, shared by every scene.

The day has 4 stages. Each horse race moves the day on one stage, and
sleeping moves it on two.
"""

STAGES = ["Morning", "Midday", "Noon", "Night"]

stage = 0   # index into STAGES; the game starts in the morning
day_index = 0


def reset() -> None:
    """Return time to the start of a new playthrough."""
    global stage, day_index
    stage = 0
    day_index = 0


def name() -> str:
    """Name of the current stage, e.g. "Noon"."""
    return STAGES[stage]


def is_night() -> bool:
    """The track is empty and the shop and Glue are closed at night."""
    return STAGES[stage] == "Night"


def can_sleep() -> bool:
    """Sleeping is available at every stage."""
    return True


def advance(count: int = 1) -> int:
    """Move time forward and return the number of full days that passed."""
    global day_index, stage
    total = stage + count
    days_passed = total // len(STAGES)
    day_index += days_passed
    stage = total % len(STAGES)
    return days_passed