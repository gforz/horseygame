"""
farm.py — The farm scene.

Shows the yard: sky, fenced pen with a little house, the shed and the van
trailer. The horses you have caught stand in the van (physics horses built
from their own traits). Drag them out of the van into the fenced pen, where
they can't get out - or drag them back into the van. Put two horses in the
shed and close its doors to breed a random half-size foal.

Press ESC to go back to the world. Closing the window also quits the game.
"""

import random

import pygame

import constants as C
import ragdoll
from classes import WorldHorse
from methods import build_horse_sprite, draw_horses, roll_world_horse_traits
from shop import get_pixel_hay_sprite, sync_hay

DISPLAY_FLAGS = pygame.SCALED | pygame.RESIZABLE

def get_screen() -> pygame.Surface:
    """Return the game window, creating it only if it doesn't exist yet."""
    surf = pygame.display.get_surface()
    if surf is None or surf.get_size() != (C.WIDTH, C.HEIGHT):
        surf = pygame.display.set_mode((C.WIDTH, C.HEIGHT), DISPLAY_FLAGS)
    return surf


BASE_W, BASE_H = 742, 419

SKY        = (130, 200, 245)
GROUND     = (255, 255, 130)
FENCE      = (255, 170, 50)
FENCE_DARK = (230, 140, 30)
HOUSE      = (245, 165, 75)
HOUSE_DARK = (215, 130, 45)
ROOF       = (225, 125, 35)
WINDOW     = (255, 240, 200)
SHED_ROOF  = (190, 100, 40)
SHED_LIGHT = (240, 160, 60)
SHED_WALL  = (205, 115, 45)
SHED_IN    = (165, 85, 35)
VAN_BORDER = (130, 200, 240)
VAN_FILL   = (255, 255, 255)
VAN_BED    = (150, 150, 160)
WHEEL      = (20, 20, 20)
HUB        = (200, 200, 205)


def _draw_fence(surf: pygame.Surface, rect: pygame.Rect) -> None:
    """Orange wooden fence enclosing `rect`."""
    t = 6

    for y in (rect.top, rect.top + 18, rect.bottom - 28, rect.bottom - 10):
        pygame.draw.rect(surf, FENCE, (rect.left, y, rect.width, t))

    for x in (rect.left, rect.right - t):
        pygame.draw.rect(surf, FENCE, (x, rect.top, t, rect.height))

    for x in range(rect.left, rect.right, 44):
        pygame.draw.rect(surf, FENCE_DARK, (x, rect.top - 2, 8, 28))
        pygame.draw.rect(surf, FENCE_DARK, (x, rect.bottom - 32, 8, 28))

    pygame.draw.rect(surf, FENCE_DARK, (rect.right - 8, rect.top - 2, 8, 28))
    pygame.draw.rect(surf, FENCE_DARK, (rect.right - 8, rect.bottom - 32, 8, 28))


def _draw_house(surf: pygame.Surface) -> None:
    pygame.draw.polygon(surf, ROOF, [(190, 26), (210, 0), (282, 0), (300, 26)])
    pygame.draw.rect(surf, HOUSE, (203, 26, 84, 34))
    pygame.draw.rect(surf, WINDOW, (216, 32, 16, 14))
    pygame.draw.rect(surf, WINDOW, (258, 32, 16, 14))
    pygame.draw.rect(surf, HOUSE_DARK, (216, 32, 16, 14), 2)
    pygame.draw.rect(surf, HOUSE_DARK, (258, 32, 16, 14), 2)

    for x, c in ((212, (235, 90, 130)), (224, (235, 90, 130)),
                 (262, (235, 90, 130)), (274, (235, 90, 130))):
        pygame.draw.rect(surf, (90, 170, 80), (x, 56, 6, 4))
        pygame.draw.rect(surf, c, (x + 1, 52, 4, 4))


def _draw_shed(surf: pygame.Surface) -> None:
    pygame.draw.rect(surf, SHED_WALL, (386, 78, 316, 126))
    pygame.draw.rect(surf, SHED_IN, (402, 88, 284, 108))
    pygame.draw.rect(surf, (140, 70, 25), (402, 190, 284, 8))
    pygame.draw.polygon(surf, SHED_ROOF, [(375, 84), (544, 0), (713, 84)])
    pygame.draw.polygon(surf, SHED_LIGHT, [(418, 70), (451, 53), (451, 70)])
    pygame.draw.polygon(surf, SHED_LIGHT, [(637, 53), (670, 70), (637, 70)])
    pygame.draw.rect(surf, SHED_ROOF, (375, 80, 338, 8))
    pygame.draw.rect(surf, (245, 205, 75), (394, 126, 8, 24))
    pygame.draw.circle(surf, (110, 65, 30), (398, 138), 2)


def _draw_van(surf: pygame.Surface) -> None:
    pygame.draw.rect(surf, VAN_BED, (445, 365, 130, 32))
    pygame.draw.rect(surf, VAN_BORDER, (372, 250, 358, 142))
    pygame.draw.rect(surf, VAN_FILL, (380, 258, 342, 126))

    for cx in (475, 535):
        pygame.draw.circle(surf, WHEEL, (cx, 398), 22)
        pygame.draw.circle(surf, HUB, (cx, 398), 7)


def _draw_grass(surf: pygame.Surface) -> None:
    """Grass ground with darker/lighter tufts and flowers."""
    rng = random.Random(7)
    sky_h = 66
    pygame.draw.rect(surf, C.GRASS, (0, sky_h, BASE_W, BASE_H - sky_h))

    for _ in range(300):
        x = rng.randint(0, BASE_W - 5)
        y = rng.randint(sky_h, BASE_H - 5)
        pygame.draw.rect(
            surf,
            rng.choice([C.DARK_GRASS, C.LIGHT_GRASS, C.GRASS]),
            (x, y, 5, 5),
        )

    for _ in range(10):
        x = rng.randint(0, BASE_W - 16)
        y = rng.randint(sky_h + 6, BASE_H - 14)
        pygame.draw.rect(surf, C.DARK_GRASS, (x, y, 14, 7))
        pygame.draw.rect(surf, C.LIGHT_GRASS, (x + 5, y + 7, 9, 5))

    for _ in range(45):
        x = rng.randint(0, BASE_W - 4)
        y = rng.randint(sky_h, BASE_H - 4)
        pygame.draw.rect(
            surf,
            rng.choice([(255, 225, 130), (245, 170, 180), (230, 230, 245)]),
            (x, y, 3, 3),
        )


def build_farm_scene() -> pygame.Surface:
    """Render the farm background."""
    surf = pygame.Surface((BASE_W, BASE_H))
    surf.fill(SKY)
    _draw_grass(surf)
    _draw_shed(surf)
    _draw_house(surf)
    _draw_van(surf)
    return surf


def build_fence_overlay() -> pygame.Surface:
    """The pen fence on a transparent surface."""
    surf = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
    _draw_fence(surf, pygame.Rect(14, 42, 310, 198))
    return surf


def build_shed_doors() -> pygame.Surface:
    """Draw the closed shed doors."""
    surf = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
    pygame.draw.rect(surf, SHED_WALL, (402, 88, 284, 108))
    pygame.draw.rect(surf, (125, 62, 28), (402, 88, 284, 108), 5)
    pygame.draw.rect(surf, SHED_LIGHT, (406, 92, 134, 100))
    pygame.draw.rect(surf, SHED_LIGHT, (544, 92, 138, 100))
    pygame.draw.line(surf, SHED_WALL, (406, 92), (540, 192), 4)
    pygame.draw.line(surf, SHED_WALL, (540, 92), (406, 192), 4)
    pygame.draw.line(surf, SHED_WALL, (544, 92), (682, 192), 4)
    pygame.draw.line(surf, SHED_WALL, (682, 92), (544, 192), 4)
    pygame.draw.circle(surf, (110, 65, 30), (540, 142), 4)
    pygame.draw.circle(surf, (110, 65, 30), (548, 142), 4)
    return surf


PEN_ZONE = pygame.Rect(14, 42, 310, 198)
PEN_AREA = pygame.Rect(22, 50, 294, 176)
VAN_ZONE = pygame.Rect(372, 250, 358, 142)
VAN_AREA = pygame.Rect(382, 258, 338, 126)
SHED_ZONE = pygame.Rect(386, 78, 316, 126)
SHED_AREA = pygame.Rect(402, 88, 284, 108)
SHED_HANDLE_ZONE = pygame.Rect(392, 124, 14, 32)
SLEEP_BUTTON_ZONE = pygame.Rect(BASE_W - 90, 12, 78, 28)
BREEDING_TIME = 3.0


def _can_breed(horses: list[WorldHorse]) -> bool:
    return (
        len(horses) == 2
        and all(
            ragdoll.ensure_stats(horse.traits)["energy"] != "Tired"
            for horse in horses
        )
    )


def run_farm(van_inventory: list, pen_horses: list, hay_items: list | None = None) -> None:
    """Show the farm until the player presses ESC."""
    screen = get_screen()
    # Use the one hay store shared with the shop (merges in anything passed in)
    hay_items = sync_hay(hay_items)
    pygame.display.set_caption("Farm")
    clock = pygame.time.Clock()

    scene = pygame.transform.scale(build_farm_scene(), (C.WIDTH, C.HEIGHT))
    fence = pygame.transform.scale(build_fence_overlay(), (C.WIDTH, C.HEIGHT))
    closed_shed_doors = pygame.transform.scale(
        build_shed_doors(), (C.WIDTH, C.HEIGHT)
    )

    sx, sy = C.WIDTH / BASE_W, C.HEIGHT / BASE_H

    def to_screen(r: pygame.Rect) -> pygame.Rect:
        return pygame.Rect(
            int(r.x * sx), int(r.y * sy),
            int(r.w * sx), int(r.h * sy),
        )

    pen_zone, pen_area = to_screen(PEN_ZONE), to_screen(PEN_AREA)
    van_zone, van_area = to_screen(VAN_ZONE), to_screen(VAN_AREA)
    shed_zone, shed_area = to_screen(SHED_ZONE), to_screen(SHED_AREA)
    shed_handle_zone = to_screen(SHED_HANDLE_ZONE)
    sleep_button_zone = to_screen(SLEEP_BUTTON_ZONE)

    # HAY POSITION HELPERS
    def get_hay_position(item: dict) -> tuple[int, int]:
        """Get a hay bale's screen position, whether it is in the van or farm."""
        if item.get("location") == "farm":
            return (
                int(item.get("farm_x", 0.5) * C.WIDTH),
                int(item.get("farm_y", 0.5) * C.HEIGHT),
            )

        return (
            van_area.left + int(item.get("rel_x", 0.5) * van_area.width),
            van_area.top + int(item.get("rel_y", 0.5) * van_area.height),
        )

    def save_hay_position(item: dict, hx: int, hy: int, settle: bool = False) -> None:
        """Save hay in the van if dropped there, otherwise in the farm.

        With settle=True (when you let go) the hay is tidied up: kept fully
        inside the van, or pushed fully outside the van walls so it never
        sits clipped into them.
        """
        hay_w, hay_h = get_pixel_hay_sprite(max(2, int(C.WIDTH / 330))).get_size()

        if van_area.collidepoint(hx, hy):
            if settle:
                hx = max(van_area.left + hay_w // 2,
                         min(van_area.right - hay_w // 2, hx))
                hy = max(van_area.top + hay_h // 2,
                         min(van_area.bottom - hay_h // 2, hy))
            item["location"] = "van"
            item["rel_x"] = (
                hx - van_area.left
            ) / float(max(1, van_area.width))
            item["rel_y"] = (
                hy - van_area.top
            ) / float(max(1, van_area.height))
            item.pop("farm_x", None)
            item.pop("farm_y", None)
        else:
            if settle:
                rect = pygame.Rect(0, 0, hay_w, hay_h)
                rect.center = (hx, hy)
                if rect.colliderect(van_zone):
                    # Push out the shortest way: left, right, up or down
                    moves = [
                        (rect.right - van_zone.left, -1, 0),
                        (van_zone.right - rect.left, 1, 0),
                        (rect.bottom - van_zone.top, 0, -1),
                        (van_zone.bottom - rect.top, 0, 1),
                    ]
                    amount, mx, my = min(moves)
                    hx += mx * amount
                    hy += my * amount
                    hx = max(hay_w // 2, min(C.WIDTH - hay_w // 2, hx))
                    hy = max(hay_h // 2, min(C.HEIGHT - hay_h // 2, hy))
            item["location"] = "farm"
            item["farm_x"] = hx / float(max(1, C.WIDTH))
            item["farm_y"] = hy / float(max(1, C.HEIGHT))

    space = ragdoll.create_space()
    ragdoll.add_box_walls(space, pen_area)
    ragdoll.add_box_walls(space, van_area)
    ragdoll.add_box_walls(space, shed_area)

    rags: list = []

    def add_ragdoll(horse, zone: str, area: pygame.Rect):
        horse.farm_zone = zone
        race, parts = ragdoll.build_ragdoll(
            space, len(rags), area, horse.traits
        )
        rag = ragdoll.Ragdoll(horse, race, parts, zone=zone)

        # If the horse is already dead when added, instantly kill its ragdoll joints
        if horse.traits.get("dead", False):
            kill_ragdoll(rag, immediate=True)

        rags.append(rag)
        return rag

    def place_in_shed(rag, horizontal_position: float) -> None:
        race = rag.race
        x = shed_area.left + shed_area.width * horizontal_position
        y = (
            shed_area.bottom - 4
            - race.torso_height / 2 * C.SCALE * race.size_scale
            - max(race.leg_lengths) - 2
        )
        ragdoll.move_horse_by(
            race, x - race.torso.position.x, y - race.torso.position.y
        )
        ragdoll.place_inside(race, shed_area)

    def place_in_pen(rag, horizontal_position: float) -> None:
        race = rag.race
        x = pen_area.left + pen_area.width * horizontal_position
        y = (
            pen_area.bottom - 4
            - race.torso_height / 2 * C.SCALE * race.size_scale
            - max(race.leg_lengths) - 2
        )
        ragdoll.move_horse_by(
            race, x - race.torso.position.x, y - race.torso.position.y
        )
        ragdoll.place_inside(race, pen_area)

    for h in van_inventory:
        add_ragdoll(h, "van", van_area)

    for h in pen_horses:
        zone = getattr(h, "farm_zone", "pen")
        area = shed_area if zone == "shed" else pen_area
        add_ragdoll(h, zone, area)

    drag = {"rag": None, "ox": 0.0, "oy": 0.0, "hay": None, "hay_ox": 0, "hay_oy": 0}
    selected = None
    acc = 0.0
    shed_doors_open = True
    breeding_remaining = 0.0
    status_message = ""
    status_timer = 0.0

    status_font = pygame.font.SysFont(
        "Arial", max(16, int(22 * C.U)), bold=True
    )
    sleep_button_font = pygame.font.SysFont(
        "Arial", max(14, int(18 * C.U)), bold=True
    )

    def shed_rags() -> list:
        return [rag for rag in rags if rag.zone == "shed"]

    def breeding_ready(parents: list) -> bool:
        return _can_breed([parent.world_horse for parent in parents])

    def kill_ragdoll(rag, immediate: bool = False) -> None:
        """Disable motors and remove all joint angle limits so the horse is completely floppy."""
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

        for part in rag.parts:
            body = getattr(part, "native", None)
            if body is not None:
                body.awake = True

    def handle_sleep() -> None:
        nonlocal status_message, status_timer, selected

        if selected in rags and selected.world_horse.traits.get("dead", False):
            selected = None

        for rag in list(rags):
            h = rag.world_horse
            traits = h.traits

            if traits.get("dead", False):
                continue

            stats = ragdoll.ensure_stats(traits)

            if stats.get("hunger") == "Starving" or traits.get("hunger") == "Starving":
                kill_ragdoll(rag)
                continue

            traits["age"] = traits.get("age", 0) + 1

            if traits["age"] >= 17:
                kill_ragdoll(rag)
                continue

            current_hunger = traits.get("hunger", "Full")

            if current_hunger in ("Full", "Fed"):
                traits["hunger"] = "Hungry"
            elif current_hunger == "Hungry":
                traits["hunger"] = "Starving"

            if traits["age"] == 1:
                traits["size_scale"] = 1.0
                sprite_right = build_horse_sprite(traits)
                sprite_left = pygame.transform.flip(
                    sprite_right, True, False
                )
                h.sprite_right = sprite_right
                h.sprite_left = sprite_left

            if stats.get("energy") == "Tired":
                traits["energy"] = "Awake"

        status_message = "A day passed. Horses aged, got hungrier, and rested."
        status_timer = 3.0

    def toggle_shed_doors() -> None:
        nonlocal shed_doors_open, breeding_remaining
        nonlocal status_message, status_timer

        if shed_doors_open:
            parents = shed_rags()

            if breeding_ready(parents):
                shed_doors_open = False
                breeding_remaining = BREEDING_TIME
                status_message = ""
            elif len(parents) == 2:
                status_message = "Tired horses cannot breed. Let them rest first."
                status_timer = 3.0
            else:
                status_message = "Place exactly 2 horses in the shed first."
                status_timer = 3.0
        elif breeding_remaining <= 0:
            shed_doors_open = True

    def complete_breeding() -> None:
        nonlocal breeding_remaining, shed_doors_open
        nonlocal status_message, status_timer

        parents = shed_rags()

        if not breeding_ready(parents):
            shed_doors_open = True
            breeding_remaining = 0.0
            status_message = (
                "Breeding stopped: tired horses cannot breed."
                if len(parents) == 2
                else "Breeding stopped: the shed needs exactly 2 horses."
            )
            status_timer = 3.0
            return

        for index, parent in enumerate(parents):
            parent.world_horse.traits["energy"] = "Tired"
            ragdoll.freeze(parent.race)
            place_in_shed(parent, 0.25 if index == 0 else 0.75)

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
        sprite_right = pygame.transform.smoothscale(
            sprite_right, baby_size
        )
        sprite_left = pygame.transform.flip(sprite_right, True, False)

        baby = WorldHorse(
            traits, sprite_right, sprite_left,
            x=float(shed_area.centerx),
            y=float(shed_area.bottom - 8),
        )
        baby.farm_zone = "shed"
        pen_horses.append(baby)

        baby_rag = add_ragdoll(baby, "shed", shed_area)
        place_in_shed(baby_rag, 0.5)

        shed_doors_open = True
        breeding_remaining = 0.0
        status_message = "A new foal was born!"
        status_timer = 3.0

    def drop(rag, pos) -> None:
        """Let go of a dragged horse."""
        if (
            shed_doors_open
            and shed_zone.collidepoint(pos)
            and (rag.zone == "shed" or len(shed_rags()) < 2)
        ):
            target = "shed"
        elif pen_zone.collidepoint(pos):
            target = "pen"
        elif van_zone.collidepoint(pos):
            target = "van"
        else:
            target = rag.zone

        if target != rag.zone:
            source = van_inventory if rag.zone == "van" else pen_horses
            destination = van_inventory if target == "van" else pen_horses

            if rag.zone == "shed":
                source = pen_horses

            if target == "shed":
                source.remove(rag.world_horse)
                if rag.world_horse not in pen_horses:
                    pen_horses.append(rag.world_horse)
            elif target == "pen" and rag.zone == "shed":
                pass
            else:
                source.remove(rag.world_horse)
                if rag.world_horse not in destination:
                    destination.append(rag.world_horse)

            rag.zone = target
            rag.world_horse.farm_zone = target

        ragdoll.freeze(rag.race)

        area = {
            "pen": pen_area,
            "van": van_area,
            "shed": shed_area,
        }[target]

        ragdoll.place_inside(rag.race, area)
        ragdoll.set_drag_collisions(rag, enabled=True)

    while True:
        dt = min(clock.tick(C.FPS_WORLD) / 1000.0, 0.033)
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if drag["rag"] is not None:
                    drop(drag["rag"], mouse_pos)
                if breeding_remaining > 0:
                    complete_breeding()
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if breeding_remaining > 0:
                    complete_breeding()
                if drag["rag"] is not None:
                    drop(drag["rag"], mouse_pos)
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                toggle_shed_doors()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if sleep_button_zone.collidepoint(event.pos):
                    handle_sleep()
                    continue

                if drag["rag"] is None and drag["hay"] is None:
                    # Check hay first so it can be picked up even near a horse.
                    hay_sprite = get_pixel_hay_sprite(max(2, int(C.WIDTH / 330)))
                    hay_rect = hay_sprite.get_rect()

                    for item in reversed(hay_items):
                        hx, hy = get_hay_position(item)
                        hay_rect.center = (hx, hy)

                        if hay_rect.collidepoint(event.pos):
                            drag["hay"] = item
                            drag["hay_ox"] = hx - event.pos[0]
                            drag["hay_oy"] = hy - event.pos[1]
                            break

                    if drag["hay"] is not None:
                        continue

                    if breeding_remaining > 0:
                        continue

                    if shed_handle_zone.collidepoint(event.pos):
                        toggle_shed_doors()
                        continue

                    if shed_zone.collidepoint(event.pos):
                        horse_clicked = any(
                            rag.zone == "shed"
                            and rag.race.rect().collidepoint(event.pos)
                            for rag in reversed(rags)
                        )

                        if not shed_doors_open and breeding_remaining > 0:
                            continue

                        if shed_doors_open and not horse_clicked:
                            toggle_shed_doors()
                        elif not shed_doors_open and breeding_remaining <= 0:
                            toggle_shed_doors()

                        if not horse_clicked:
                            continue

                    for rag in reversed(rags):
                        if rag.race.rect().collidepoint(event.pos):
                            torso = rag.race.torso
                            drag["rag"] = rag
                            drag["ox"] = torso.position.x - event.pos[0]
                            drag["oy"] = torso.position.y - event.pos[1]
                            ragdoll.freeze(rag.race)
                            ragdoll.set_drag_collisions(rag, enabled=False)
                            acc = 0.0
                            break

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                hit = None

                for rag in reversed(rags):
                    if rag.race.rect().collidepoint(event.pos):
                        if not rag.world_horse.traits.get("dead", False):
                            hit = rag
                        break

                selected = None if hit is selected else hit

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if drag["hay"] is not None:
                    hay_sprite = get_pixel_hay_sprite(max(2, int(C.WIDTH / 330)))
                    hay_sw, hay_sh = hay_sprite.get_size()

                    hx = event.pos[0] + drag["hay_ox"]
                    hy = event.pos[1] + drag["hay_oy"]

                    hx = max(
                        hay_sw // 2,
                        min(C.WIDTH - hay_sw // 2, hx)
                    )
                    hy = max(
                        hay_sh // 2,
                        min(C.HEIGHT - hay_sh // 2, hy)
                    )

                    save_hay_position(drag["hay"], hx, hy, settle=True)
                    drag["hay"] = None

                elif drag["rag"] is not None:
                    drop(drag["rag"], event.pos)
                    drag["rag"] = None
                    acc = 0.0

        # Move the selected hay item anywhere in the farm.
        if drag["hay"] is not None:
            hay_sprite = get_pixel_hay_sprite(max(2, int(C.WIDTH / 330)))
            hay_sw, hay_sh = hay_sprite.get_size()

            hx = mouse_pos[0] + drag["hay_ox"]
            hy = mouse_pos[1] + drag["hay_oy"]

            hx = max(
                hay_sw // 2,
                min(C.WIDTH - hay_sw // 2, hx)
            )
            hy = max(
                hay_sh // 2,
                min(C.HEIGHT - hay_sh // 2, hy)
            )

            save_hay_position(drag["hay"], hx, hy)

        if drag["rag"] is not None:
            torso = drag["rag"].race.torso
            ragdoll.move_horse_by(
                drag["rag"].race,
                mouse_pos[0] + drag["ox"] - torso.position.x,
                mouse_pos[1] + drag["oy"] - torso.position.y,
            )

        # Dead horses do not run their normal walking animation.
        for rag in rags:
            if not rag.world_horse.traits.get("dead", False):
                rag.race.update(
                    dt, is_dragged=(rag is drag["rag"])
                )

        if breeding_remaining > 0:
            breeding_remaining = max(0.0, breeding_remaining - dt)
            if breeding_remaining == 0:
                complete_breeding()
        elif status_timer > 0:
            status_timer = max(0.0, status_timer - dt)
            if status_timer == 0:
                status_message = ""

        acc += dt
        while acc >= C.PHYSICS_STEP:
            space.step(C.PHYSICS_STEP)
            acc -= C.PHYSICS_STEP

        screen.blit(scene, (0, 0))

        ordered = [r.race for r in rags if r is not drag["rag"]]
        if drag["rag"] is not None:
            ordered.append(drag["rag"].race)

        draw_horses(screen, ordered)

        # Draw hay in the van or wherever it has been placed on the farm.
        hay_sprite = get_pixel_hay_sprite(max(2, int(C.WIDTH / 330)))
        hay_sw, hay_sh = hay_sprite.get_size()

        for item in hay_items:
            hx, hy = get_hay_position(item)

            if drag["hay"] is item:
                shadow_w = max(1, int(hay_sw * 1.1))
                shadow_h = max(1, int(hay_sh * 0.3))
                shadow_surf = pygame.Surface(
                    (shadow_w, shadow_h), pygame.SRCALPHA
                )
                pygame.draw.ellipse(
                    shadow_surf,
                    (0, 0, 0, 60),
                    (0, 0, shadow_w, shadow_h)
                )
                screen.blit(
                    shadow_surf,
                    (hx - shadow_w // 2, hy + hay_sh // 2 + 4)
                )

            screen.blit(
                hay_sprite,
                hay_sprite.get_rect(center=(hx, hy))
            )

        screen.blit(fence, (0, 0))

        if not shed_doors_open:
            screen.blit(closed_shed_doors, (0, 0))

        sleep_btn_rect = to_screen(SLEEP_BUTTON_ZONE)
        pygame.draw.rect(
            screen, (70, 130, 180), sleep_btn_rect, border_radius=6
        )
        pygame.draw.rect(
            screen, (255, 255, 255), sleep_btn_rect, 2, border_radius=6
        )

        sleep_label = sleep_button_font.render(
            "Sleep", True, (255, 255, 255)
        )
        screen.blit(
            sleep_label,
            sleep_label.get_rect(center=sleep_btn_rect.center),
        )

        shed_count = len(shed_rags())

        if breeding_remaining > 0:
            message = f"Breeding... {breeding_remaining:.1f}s"
        elif status_message:
            message = status_message
        elif shed_count == 2 and breeding_ready(shed_rags()):
            message = "2 horses ready - click the handle or press Space"
        elif shed_count == 2:
            message = "Tired horses cannot breed. Let them rest first."
        else:
            message = "Place 2 horses in the shed, then click the handle or press Space"

        label = status_font.render(message, True, (255, 255, 255))
        label_rect = label.get_rect(
            midbottom=(C.WIDTH // 2, C.HEIGHT - 14)
        )

        pygame.draw.rect(
            screen, (65, 42, 20),
            label_rect.inflate(24, 14),
            border_radius=8,
        )
        screen.blit(label, label_rect)

        if (
            selected is not None
            and not selected.world_horse.traits.get("dead", False)
        ):
            ragdoll.draw_stats_panel(
                screen, selected.race, selected.world_horse.traits
            )

        pygame.display.flip()
