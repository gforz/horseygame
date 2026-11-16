"""horse_care.py — Looking after caught horses: ageing, feeding, breeding.

These are the rules that do not care which scene a horse is standing in, so
the farm, the van and the scale house can all share them.
"""

import random

import pygame

from game import constants as C
from game import state
from game.gfx.horse_model import get_back_leg_swing, roll_world_horse_traits
from game.gfx.world_horse_sprite import build_horse_sprite
from game.sim.ragdoll import ensure_stats

HERITABLE_TRAITS = (
    "back_length",
    "front_length",
    "back_hip_x",
    "front_hip_x",
    "start_angle",
    "hoof_length",
    "hoof_shape",
    "torso_length",
    "torso_height",
    "tail_length",
    "tail_width",
    "front_leg_force",
    "back_leg_swing",
)


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


def advance_wild_foal_day(horse) -> bool:
    """Grow a wild foal up after one day without applying farm hunger rules."""
    traits = horse.traits
    if traits.get("size_scale", 1.0) >= 1.0:
        return False

    traits["age"] = traits.get("age", 0) + 1
    traits["size_scale"] = 1.0
    traits["energy"] = "Awake"
    horse.sprite_right, horse.sprite_left = sprites_for(traits)
    horse.w, horse.h = horse.sprite_right.get_size()
    return True


def _random_mutation_value(trait: str, traits: dict):
    if trait == "back_length" or trait == "front_length":
        return random.uniform(C.MIN_LEG_LENGTH, C.MAX_LEG_LENGTH)
    if trait == "back_hip_x" or trait == "front_hip_x":
        hip_limit = traits["torso_length"] / 2 - C.TORSO_HIP_INSET
        return random.uniform(
            C.MODEL_CENTRE_X - hip_limit,
            C.MODEL_CENTRE_X + hip_limit,
        )
    if trait == "start_angle":
        return random.uniform(C.MIN_START_ANGLE, C.MAX_START_ANGLE)
    if trait == "hoof_length":
        if traits["hoof_shape"] == C.HOOF_SHAPE_FORWARD_RECT:
            return random.uniform(
                C.HOOF_FORWARD_RECT_LENGTH_MIN,
                C.HOOF_FORWARD_RECT_LENGTH_MAX,
            )
        return random.uniform(C.HOOF_LENGTH_MIN, C.HOOF_LENGTH_MAX)
    if trait == "hoof_shape":
        return random.choice(C.HOOF_SHAPES)
    if trait == "torso_length":
        return random.uniform(C.TORSO_LENGTH_MIN, C.TORSO_LENGTH_MAX)
    if trait == "torso_height":
        return random.uniform(C.TORSO_HEIGHT_MIN, C.TORSO_HEIGHT_MAX)
    if trait == "tail_length":
        return random.uniform(C.TAIL_LENGTH_MIN, C.TAIL_LENGTH_MAX)
    if trait == "tail_width":
        return random.uniform(C.TAIL_WIDTH_MIN, C.TAIL_WIDTH_MAX)
    if trait == "front_leg_force":
        return random.uniform(C.MIN_FRONT_LEG_FORCE, C.MAX_FRONT_LEG_FORCE)
    if trait == "back_leg_swing":
        return random.uniform(
            min(C.BACK_LEG_SWING_SHORT, C.BACK_LEG_SWING_LONG)
            - C.BACK_LEG_SWING_VARIATION,
            max(C.BACK_LEG_SWING_SHORT, C.BACK_LEG_SWING_LONG)
            + C.BACK_LEG_SWING_VARIATION,
        )
    raise ValueError(f"Unknown heritable trait: {trait}")


def _inherited_color(color_a: tuple[int, int, int],
                     color_b: tuple[int, int, int]) -> tuple[int, int, int]:
    if random.random() < 0.5:
        color = random.choice((color_a, color_b))
        if random.random() >= 0.2:
            return color
        return tuple(
            max(0, min(255, channel + random.randint(-12, 12)))
            for channel in color
        )

    blend = random.uniform(0.4, 0.6)
    return tuple(
        round(a * blend + b * (1.0 - blend))
        for a, b in zip(color_a, color_b)
    )


def inherit_traits(parent_a: dict, parent_b: dict) -> dict:
    """Create genetic traits by independently inheriting from either parent."""
    for parent in (parent_a, parent_b):
        parent.setdefault(
            "front_leg_force",
            random.uniform(C.MIN_FRONT_LEG_FORCE, C.MAX_FRONT_LEG_FORCE),
        )
        parent.setdefault(
            "back_leg_swing",
            get_back_leg_swing(parent["back_length"]),
        )

    traits = roll_world_horse_traits()
    for trait in HERITABLE_TRAITS:
        inherited_values = [
            parent[trait]
            for parent in (parent_a, parent_b)
            if trait in parent
        ]
        if inherited_values:
            traits[trait] = random.choice(inherited_values)

    traits["color"] = _inherited_color(parent_a["color"], parent_b["color"])

    mutation_chance = 0.1
    while random.random() < mutation_chance:
        trait = random.choice(HERITABLE_TRAITS)
        traits[trait] = _random_mutation_value(trait, traits)
        mutation_chance *= 0.1

    hip_limit = traits["torso_length"] / 2 - C.TORSO_HIP_INSET
    traits["back_hip_x"] = max(
        C.MODEL_CENTRE_X - hip_limit,
        min(C.MODEL_CENTRE_X + hip_limit, traits["back_hip_x"]),
    )
    traits["front_hip_x"] = max(
        C.MODEL_CENTRE_X - hip_limit,
        min(C.MODEL_CENTRE_X + hip_limit, traits["front_hip_x"]),
    )
    hoof_length_bounds = (
        (C.HOOF_FORWARD_RECT_LENGTH_MIN, C.HOOF_FORWARD_RECT_LENGTH_MAX)
        if traits["hoof_shape"] == C.HOOF_SHAPE_FORWARD_RECT
        else (C.HOOF_LENGTH_MIN, C.HOOF_LENGTH_MAX)
    )
    traits["hoof_length"] = max(
        hoof_length_bounds[0],
        min(hoof_length_bounds[1], traits["hoof_length"]),
    )

    traits["size_scale"] = 0.5
    traits["age"] = 0
    traits["hunger"] = "Hungry"
    traits["energy"] = "Tired"
    traits["dead"] = False
    return traits


def new_foal(
    parent_a: dict,
    parent_b: dict,
) -> tuple[dict, pygame.Surface, pygame.Surface]:
    """Build a half-size newborn foal from both parents' traits."""
    traits = inherit_traits(parent_a, parent_b)

    sprite_right = build_horse_sprite(traits)
    baby_size = (
        max(1, round(sprite_right.get_width() * 0.5)),
        max(1, round(sprite_right.get_height() * 0.5)),
    )
    sprite_right = pygame.transform.smoothscale(sprite_right, baby_size)
    sprite_left = pygame.transform.flip(sprite_right, True, False)
    return traits, sprite_right, sprite_left