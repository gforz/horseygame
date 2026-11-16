"""horse_care.py — Looking after caught horses: ageing, feeding, breeding.

These are the rules that do not care which scene a horse is standing in, so
the farm, the van and the scale house can all share them.
"""

import pygame

from game import state
from game.gfx.horse_model import roll_world_horse_traits
from game.gfx.world_horse_sprite import build_horse_sprite
from game.sim.ragdoll import ensure_stats


def can_breed(horses: list) -> bool:
    """Two horses that are both awake can produce a foal."""
    return (
        len(horses) == 2
        and all(
            ensure_stats(horse.traits)["energy"] != "Tired"
            for horse in horses
        )
    )


def mouth_rect_of(rag) -> pygame.Rect:
    """Rough mouth area: the lower front part of the horse's head."""
    head = rag.race.head.rect()
    w = max(4, int(head.width * 0.45))
    h = max(4, int(head.height * 0.65))
    return pygame.Rect(head.right - w, head.bottom - h, w, h)


def kill_ragdoll(rag, wake: bool = True) -> None:
    """Make a horse completely floppy: no motors, no joint limits.

    Also flags the horse as dead on its traits so every scene agrees.
    """
    rag.world_horse.traits["dead"] = True

    for leg in rag.race.legs:
        joint = leg.motor
        joint.enableMotor = False
        joint.enableLimit = False
        joint.motorSpeed = 0.0
        joint.maxMotorTorque = 0.0
        if hasattr(joint, "lower_limit"):
            joint.lower_limit = -float("inf")
        if hasattr(joint, "upper_limit"):
            joint.upper_limit = float("inf")

    for joint in getattr(rag.race, "joints", []):
        if hasattr(joint, "enableLimit"):
            joint.enableLimit = False
        if hasattr(joint, "lower_limit"):
            joint.lower_limit = -float("inf")
        if hasattr(joint, "upper_limit"):
            joint.upper_limit = float("inf")

    if wake:
        for part in rag.parts:
            body = getattr(part, "native", None)
            if body is not None:
                body.awake = True


def age_one_day(traits: dict) -> str | None:
    """Age a horse by one full day and return why it died, if applicable.

    Starving horses and horses of 17 years or more die; everyone else gets
    hungrier and (if tired) rests.
    """
    stats = ensure_stats(traits)

    if stats.get("hunger") == "Starving" or traits.get("hunger") == "Starving":
        return "starving"

    traits["age"] = traits.get("age", 0) + 1

    if traits["age"] >= 17:
        return "old"

    current_hunger = traits.get("hunger", "Full")

    if current_hunger in ("Full", "Fed"):
        traits["hunger"] = "Hungry"
    elif current_hunger == "Hungry":
        traits["hunger"] = "Starving"

    if traits["age"] == 1:
        traits["size_scale"] = 1.0

    if stats.get("energy") == "Tired":
        traits["energy"] = "Awake"

    return None


def sprites_for(traits: dict) -> tuple[pygame.Surface, pygame.Surface]:
    """(right-facing, left-facing) sprites for a horse with these traits."""
    sprite_right = build_horse_sprite(traits)
    sprite_left = pygame.transform.flip(sprite_right, True, False)
    return sprite_right, sprite_left


def advance_horse_day(horse) -> tuple[str | None, bool]:
    """Update a horse for one new day; return its death reason and growth flag."""
    was_foal = horse.traits.get("size_scale", 1.0) < 1.0
    death_reason = age_one_day(horse.traits)
    if death_reason is not None:
        if not horse.traits.get("dead", False):
            state.horses_killed += 1
        horse.traits["dead"] = True
        return death_reason, False

    grew_up = was_foal and horse.traits["age"] == 1
    if grew_up:
        horse.sprite_right, horse.sprite_left = sprites_for(horse.traits)
        horse.w, horse.h = horse.sprite_right.get_size()
    return None, grew_up


def new_foal() -> tuple[dict, pygame.Surface, pygame.Surface]:
    """A newborn foal: half-size, asleep, hungry, and alive."""
    traits = roll_world_horse_traits()
    traits["size_scale"] = 0.5
    traits["age"] = 0
    traits["hunger"] = "Hungry"
    traits["energy"] = "Tired"
    traits["dead"] = False

    sprite_right = build_horse_sprite(traits)
    baby_size = (
        max(1, round(sprite_right.get_width() * 0.5)),
        max(1, round(sprite_right.get_height() * 0.5)),
    )
    sprite_right = pygame.transform.smoothscale(sprite_right, baby_size)
    sprite_left = pygame.transform.flip(sprite_right, True, False)
    return traits, sprite_right, sprite_left