"""ragdoll.py — Physics horses shared by the world van, the farm and the shops.

A caught WorldHorse is turned into a track-style ragdoll (torso + two motor
legs, built exactly like sim.race_setup.create_race) using the horse's own
traits. Ragdolls never collide with each other, only with the static
walls/floors you add with add_box_walls().
"""

import random

import pygame

from game import constants as C
from game.gfx.fonts import get_font
from game.gfx.horse_model import (
    get_back_leg_swing,
    get_random_hoof,
    hoof_vertices,
    torso_mass_for_size,
)
from game.physics import PhysicsSpace, torque_to_box2d
from game.sim.horse_parts import (
    Leg,
    create_horse_head,
    create_horse_tail,
)
from game.sim.race_horse import RaceHorse

GROUP = 99   # one shared shape group -> horses never collide with each other


class Ragdoll:
    """A caught horse living in a physics space (van or farm)."""

    def __init__(self, world_horse, race_horse: RaceHorse, parts: list,
                 zone: str = "van") -> None:
        self.world_horse = world_horse   # the WorldHorse that was caught
        self.race        = race_horse    # its physics body (torso + 2 legs)
        self.parts       = parts         # Box2D bodies, for removal
        self.zone        = zone          # "van" or "pen" (used by the farm)


# ------------------------------------------------------------------
# Space / walls
# ------------------------------------------------------------------
def create_space() -> PhysicsSpace:
    """Physics world with the same settings as the race track."""
    return PhysicsSpace(C.GRAVITY)


def add_box_walls(space: PhysicsSpace, area: pygame.Rect) -> None:
    """Floor at the bottom of `area` plus tall left/right walls, so horses
    inside can't get out (there is no ceiling, the walls are just very tall)."""
    floor_y = area.bottom - 4
    top_y   = area.top - 800
    for a, b in (
        ((area.left,  floor_y), (area.right, floor_y)),   # floor
        ((area.left,  floor_y), (area.left,  top_y)),     # left wall
        ((area.right, floor_y), (area.right, top_y)),     # right wall
    ):
        space.add_edge(a, b, friction=2.5)


# ------------------------------------------------------------------
# Stats (age / hunger / energy) + the right-click info panel
# ------------------------------------------------------------------
HUNGER_LEVELS = ("Full", "Hungry", "Starving")
ENERGY_LEVELS = ("Tired", "Awake")

STAT_COLORS = {
    "Full":     (110, 210, 120),
    "Hungry":   (235, 160, 60),
    "Starving": (230, 80, 70),
    "Awake":    (110, 210, 120),
    "Tired":    (140, 170, 235),
}


def ensure_stats(traits: dict) -> dict:
    """Give a horse its stats the first time it needs them and keep them on
    its traits from then on, preserving existing state across files.
      age     : 0 - 16 years (0 for a foal)
      hunger  : "Full", "Hungry" or "Starving"
      energy  : "Tired" or "Awake"
      dead    : boolean flag
    """
    if "age" not in traits or not isinstance(traits["age"], int):
        traits["age"] = random.randint(2, 16)
    if traits.get("hunger") not in HUNGER_LEVELS:
        traits["hunger"] = random.choice(HUNGER_LEVELS)
    if traits.get("energy") not in ENERGY_LEVELS:
        traits["energy"] = random.choice(ENERGY_LEVELS)
    traits.setdefault("dead", False)
    return traits


def draw_stats_panel(screen: pygame.Surface, race: RaceHorse, traits: dict) -> None:
    """Small info panel above (or below) a horse showing its stats."""
    stats = ensure_stats(traits)
    title_font = get_font(22, bold=True)
    bold_font = get_font(18, bold=True)

    panel = pygame.Rect(0, 0, 210, 126)
    horse_rect = race.rect()
    panel.midbottom = (horse_rect.centerx, horse_rect.top - 8)
    if panel.top < 8:
        panel.midtop = (horse_rect.centerx, horse_rect.bottom + 8)
    panel.clamp_ip(screen.get_rect().inflate(-16, -16))

    pygame.draw.rect(screen, C.DARK_BROWN, panel, border_radius=10)
    pygame.draw.rect(screen, C.GOLD, panel, 3, border_radius=10)

    title = title_font.render("Horse Stats", True, C.GOLD)
    screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.top + 8)))

    def row(value: str, y: int, color: tuple) -> None:
        rendered = bold_font.render(value, True, color)
        screen.blit(rendered, rendered.get_rect(midtop=(panel.centerx, y)))

    row(f"{stats['age']} years", panel.top + 42, C.WORLD_WHITE)
    row(stats["hunger"], panel.top + 68, STAT_COLORS[stats["hunger"]])
    row(stats["energy"], panel.top + 94, STAT_COLORS[stats["energy"]])


# ------------------------------------------------------------------
# Building a horse from its traits
# ------------------------------------------------------------------
def build_ragdoll(space: PhysicsSpace, index: int, area: pygame.Rect,
                  traits: dict):
    """Build a track-style horse from a caught horse's traits, dropped into
    `area`. Returns (RaceHorse, parts)."""
    floor_y = area.bottom - 4
    parts = []
    ensure_stats(traits)
    size_scale = traits.get("size_scale", 1.0)

    leg_lengths = [
        traits["back_length"] * C.SCALE * size_scale,
        traits["front_length"] * C.SCALE * size_scale,
    ]
    hip_positions = [
        (traits["back_hip_x"] - C.MODEL_CENTRE_X) * C.SCALE * size_scale,
        (traits["front_hip_x"] - C.MODEL_CENTRE_X) * C.SCALE * size_scale,
    ]
    horse_start_angle = traits["start_angle"]
    color = traits["color"]
    front_leg_force = traits.setdefault(
        "front_leg_force",
        random.uniform(C.MIN_FRONT_LEG_FORCE, C.MAX_FRONT_LEG_FORCE),
    )
    if "back_leg_swing" not in traits:
        traits["back_leg_swing"] = get_back_leg_swing(traits["back_length"])
    if "hoof_length" not in traits or "hoof_shape" not in traits:
        hoof_length, hoof_shape = get_random_hoof()
        traits.setdefault("hoof_length", hoof_length)
        traits.setdefault("hoof_shape", hoof_shape)
    if "torso_length" not in traits:
        traits["torso_length"] = random.uniform(C.TORSO_LENGTH_MIN, C.TORSO_LENGTH_MAX)
    if "torso_height" not in traits:
        traits["torso_height"] = random.uniform(C.TORSO_HEIGHT_MIN, C.TORSO_HEIGHT_MAX)
    hoof_length = traits["hoof_length"]
    hoof_shape = traits["hoof_shape"]
    torso_length = traits["torso_length"]
    torso_height = traits["torso_height"]
    hip_limit = (torso_length / 2 - C.TORSO_HIP_INSET) * C.SCALE * size_scale
    hip_positions = [
        max(-hip_limit, min(hip_limit, hip_x))
        for hip_x in hip_positions
    ]
    if "back_hip_min_angle" not in traits:
        traits["back_hip_min_angle"] = max(
            -C.HIP_MAX_ANGLE,
            -(traits["back_leg_swing"] + random.uniform(
            C.BACK_HIP_LIMIT_MARGIN_MIN,
            C.BACK_HIP_LIMIT_MARGIN_MAX,
            )),
        )
    traits["back_hip_min_angle"] = max(
        -C.HIP_MAX_ANGLE,
        traits["back_hip_min_angle"],
    )
    back_leg_swing = traits["back_leg_swing"]
    back_hip_min_angle = traits["back_hip_min_angle"]

    margin = min(160 * C.SCALE * size_scale, area.width * 0.3)
    torso_x = random.uniform(area.left + margin, area.right - margin)
    torso_y = (
        floor_y - torso_height / 2 * C.SCALE * size_scale - max(leg_lengths)
        - random.uniform(0, 30 * size_scale)
    )
    torso = space.create_box_body(
        mass=torso_mass_for_size(torso_length, torso_height) * size_scale ** 2,
        position=(torso_x, torso_y),
        size=(
            torso_length * C.SCALE * size_scale,
            torso_height * C.SCALE * size_scale,
        ),
        angle=0,
        friction=0.8,
        group_index=GROUP,
    )
    parts.append(torso)
    head = create_horse_head(
        space, torso, torso_length, torso_height, GROUP,
        size_scale=size_scale,
    )
    parts.append(head.body)
    tail_length = traits.setdefault(
        "tail_length",
        random.uniform(C.TAIL_LENGTH_MIN, C.TAIL_LENGTH_MAX),
    )
    tail_width = traits.setdefault(
        "tail_width",
        random.uniform(C.TAIL_WIDTH_MIN, C.TAIL_WIDTH_MAX),
    )
    tail = create_horse_tail(
        space,
        torso,
        torso_length,
        torso_height,
        GROUP,
        length=tail_length,
        width=tail_width,
        size_scale=size_scale,
    )
    parts.append(tail.body)

    legs = []
    for leg_index, hip_x in enumerate(hip_positions):
        leg_length = leg_lengths[leg_index]
        hip_y = torso_height / 2 * C.SCALE * size_scale
        hip_world = torso.local_to_world((hip_x, hip_y))
        original_angle = -horse_start_angle if leg_index == 0 else horse_start_angle
        leg_body = space.create_box_body(
            mass=C.LEG_MASS * size_scale ** 2,
            position=(0, 0),
            size=(C.LEG_WIDTH * size_scale, leg_length),
            angle=torso.angle + original_angle,
            friction=2.8,
            group_index=GROUP,
        )
        hoof_center_y = leg_length / 2 - 2 * C.U * size_scale
        space.add_hoof_fixture(
            leg_body,
            vertices=tuple(
                (
                    x * C.SCALE * size_scale,
                    hoof_center_y + y * C.SCALE * size_scale,
                )
                for x, y in hoof_vertices(hoof_length, hoof_shape)
            ),
            friction=C.HOOF_FRICTION,
            group_index=GROUP,
        )
        anchor_offset = leg_body.local_to_world((0, -leg_length / 2))
        leg_body.position = (hip_world.x - anchor_offset.x,
                             hip_world.y - anchor_offset.y)

        leg_force = front_leg_force if leg_index == 1 else None
        max_motor_torque = (
            torque_to_box2d(front_leg_force) * C.LEG_MOTOR_TORQUE_SCALE
            if leg_force is not None else C.BACK_LEG_MAX_TORQUE
        )
        hip_joint = space.create_revolute_joint(
            torso,
            leg_body,
            hip_world,
            back_hip_min_angle if leg_index == 0 else C.HIP_MIN_ANGLE,
            C.HIP_MAX_ANGLE,
            max_motor_torque,
        )
        parts.append(leg_body)
        legs.append(Leg(
            body=leg_body,
            motor=hip_joint,
            hip_x=hip_x,
            motor_force=leg_force,
            original_angle=original_angle,
            swing_angle=back_leg_swing if leg_index == 0 else C.LEG_SWING_ANGLE,
            wait_time=random.uniform(C.MIN_LEG_WAIT, C.MAX_LEG_WAIT),
            move_duration=random.uniform(C.MIN_MOVE_TIME, C.MAX_MOVE_TIME),
        ))

    race_horse = RaceHorse(
        lane=index % C.LANE_COUNT,
        torso=torso,
        color=color,
        legs=legs,
        leg_lengths=leg_lengths,
        start_angle=horse_start_angle,
        head=head,
        tail=tail,
        torso_length=torso_length,
        torso_height=torso_height,
        hoof_length=hoof_length,
        hoof_shape=hoof_shape,
        size_scale=size_scale,
    )

    # If the horse was already dead from stats, apply death state immediately on spawn
    if traits.get("dead", False):
        race_horse.torso.awake = True

    return race_horse, parts


# ------------------------------------------------------------------
# Dragging helpers (same method as the race track)
# ------------------------------------------------------------------
def freeze(race: RaceHorse) -> None:
    """Zero all motion on a horse (used when grabbing / dropping it)."""
    race.torso.velocity = (0, 0)
    race.torso.angular_velocity = 0
    race.head.body.velocity = (0, 0)
    race.head.body.angular_velocity = 0
    race.head.stop()
    race.tail.body.velocity = (0, 0)
    race.tail.body.angular_velocity = 0
    race.tail.stop()
    for leg in race.legs:
        leg.body.velocity = (0, 0)
        leg.body.angular_velocity = 0
        leg.stop()


def set_drag_collisions(rag: Ragdoll, enabled: bool) -> None:
    """Disable a horse's fixture collisions while it is being dragged."""
    saved = getattr(rag, "_drag_collision_masks", None)
    if enabled:
        if saved is None:
            return
        for fixture, mask_bits in saved:
            filter_data = fixture.filterData
            filter_data.maskBits = mask_bits
            fixture.filterData = filter_data
            fixture.Refilter()
        del rag._drag_collision_masks
        return

    if saved is not None:
        return
    saved = []
    for part in rag.parts:
        for fixture in part.native.fixtures:
            filter_data = fixture.filterData
            saved.append((fixture, filter_data.maskBits))
            filter_data.maskBits = 0
            fixture.filterData = filter_data
            fixture.Refilter()
    rag._drag_collision_masks = saved


def move_horse_by(race: RaceHorse, dx: float, dy: float) -> None:
    """Shift a whole horse (torso + legs) by (dx, dy) without physics."""
    race.torso.position = (race.torso.position.x + dx, race.torso.position.y + dy)
    race.torso.velocity = (0, 0)
    race.torso.angular_velocity = 0
    race.head.body.position = (
        race.head.body.position.x + dx,
        race.head.body.position.y + dy,
    )
    race.head.body.velocity = (0, 0)
    race.head.body.angular_velocity = 0
    race.head.stop()
    race.tail.body.position = (
        race.tail.body.position.x + dx,
        race.tail.body.position.y + dy,
    )
    race.tail.body.velocity = (0, 0)
    race.tail.body.angular_velocity = 0
    race.tail.stop()
    for leg in race.legs:
        leg.body.position = (leg.body.position.x + dx, leg.body.position.y + dy)
        leg.body.velocity = (0, 0)
        leg.body.angular_velocity = 0
        leg.stop()


def place_inside(race: RaceHorse, area: pygame.Rect) -> None:
    """Nudge a dropped horse fully inside `area` before physics resumes."""
    margin = min(
        160 * C.SCALE * race.size_scale,
        area.width * 0.3,
    )
    max_y = (
        area.bottom - 4
        - race.torso_height / 2 * C.SCALE * race.size_scale
        - max(race.leg_lengths) - 2
    )
    tx = max(area.left + margin, min(area.right - margin, race.torso.position.x))
    ty = min(race.torso.position.y, max_y)
    move_horse_by(race, tx - race.torso.position.x, ty - race.torso.position.y)


def resize_ragdoll(space: PhysicsSpace, rag: Ragdoll, area: pygame.Rect) -> None:
    """Rebuild a horse's physics body at its trait-defined size."""
    old_x = rag.race.torso.position.x
    race, parts = build_ragdoll(space, rag.race.lane, area, rag.world_horse.traits)
    space.remove(*rag.parts)

    margin = min(160 * C.SCALE * race.size_scale, area.width * 0.3)
    x = max(area.left + margin, min(area.right - margin, old_x))
    y = (
        area.bottom - 4
        - race.torso_height / 2 * C.SCALE * race.size_scale
        - max(race.leg_lengths) - 2
    )
    move_horse_by(race, x - race.torso.position.x, y - race.torso.position.y)
    place_inside(race, area)
    rag.race, rag.parts = race, parts