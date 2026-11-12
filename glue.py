"""Overworld scale house and its horse-weighing scene."""

import math

import pygame

import constants as C
import ragdoll
import track
from methods import draw_horses, get_font


HOUSE_POSITION = (1850, 420)
HOUSE_INTERACT_DIST = 150
BACKGROUND = (144, 54, 54)


def build_house_sprite() -> pygame.Surface:
    """Build the transparent-backed pixel-art scale-house sprite."""
    pixels = (
        "....................KK",
        "....................KK",
        "....................KK",
        ".................KK.KK",
        ".................KK.KK",
        ".................KK.KK.....LLLL",
        "..............DDDKKDKKDDDDDDLL",
        "............DDDDDDDDDDDDDDDDDLLL",
        "..........LLDDDDDDDDDDDDDDDDDD",
        "........LLLDDDDDDDDDDDDDDDDDMM",
        "...........gggggggggggMMMMMM",
        "...........gRRRgRRRRRgMMMMMM.GY",
        "...........gggggggggggMMMMGGYY",
        "...........gRRRRRgRRRgMMMMGG",
        "...........gggggggggggMMMMGG",
        "...........gRRRgRRRRRgMMMMMM",
        "...........gggggggggggMMMMMM",
        "...........gRRRRRgRRRgMMMMSSSSSS",
        "...........gggggggggggMMMMSSSSSS",
        ".........OOgRRRgRRRRRgMMMMSSSSSS",
        ".........OOggggggggggg....KK..KK",
        ".................KK.......KK..KK",
    )
    palette = {
        ".": (0, 0, 0, 0),
        "K": (24, 22, 23),      # chimneys, wheels, feet
        "D": (132, 43, 57),     # roof
        "L": (172, 72, 78),     # roof highlight
        "M": (110, 36, 48),     # side wall
        "R": (176, 62, 66),     # bricks
        "g": (150, 150, 155),   # frame / mortar
        "G": (86, 150, 40),     # vine
        "Y": (190, 210, 70),    # vine leaves
        "S": (88, 98, 91),      # rubble
        "O": (225, 140, 40),    # orange block
    }

    pixel_size = 7
    width = max(map(len, pixels))
    sprite = pygame.Surface((width, len(pixels)), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, color in enumerate(row):
            if color != ".":
                sprite.set_at((x, y), palette[color])
    return pygame.transform.scale(sprite, (width * pixel_size, len(pixels) * pixel_size))


def near_house(player, house_rect: pygame.Rect) -> bool:
    """Return whether the player is close enough to enter the scale house."""
    return pygame.Vector2(player.x, player.y).distance_to(house_rect.midbottom) <= HOUSE_INTERACT_DIST


def _horse_weight(rag: ragdoll.Ragdoll) -> int:
    """Convert the horse's summed physics-body mass to a pound reading."""
    physics_mass = sum(part.native.mass for part in rag.parts)
    return round(physics_mass * 40)


def _sale_payout(weight: int) -> int:
    """Pay $5 for every 100 lb of horse weight, rounded to whole dollars."""
    return round(weight * 5 / 100)


def _horse_on_scale(rag: ragdoll.Ragdoll, platform: pygame.Rect, tolerance: int) -> bool:
    """Check that the horse is standing over the platform at floor height."""
    bounds = rag.race.rect()
    return (
        platform.left <= bounds.centerx <= platform.right
        and abs(bounds.bottom - platform.top) <= tolerance
    )


def _draw_van(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw the farm-style trailer body behind its physics horses."""
    van = pygame.Surface((358, 170), pygame.SRCALPHA)
    pygame.draw.rect(van, (150, 150, 160), (73, 115, 130, 32))
    pygame.draw.rect(van, (130, 200, 240), (0, 0, 358, 142))
    pygame.draw.rect(van, (255, 255, 255), (8, 8, 342, 126))
    for x in (103, 163):
        pygame.draw.circle(van, (20, 20, 20), (x, 148), 22)
        pygame.draw.circle(van, (200, 200, 205), (x, 148), 7)
    screen.blit(pygame.transform.scale(van, rect.size), rect.topleft)


def _treadmill_belt_height(rect: pygame.Rect) -> int:
    return max(16, round(rect.height * 0.6))


def _treadmill_belt_y(rect: pygame.Rect) -> int:
    """Walking surface: the top edge of the belt."""
    return rect.top


def _treadmill_layout(rect: pygame.Rect) -> dict:
    """Shared geometry for the belt and the door/house it runs into."""
    belt_h = _treadmill_belt_height(rect)
    pillar_w = round(belt_h * 2.1)
    opening_w = round(belt_h * 4.3)
    wall_w = round(belt_h * 3.1)
    belt_bottom = rect.top + belt_h
    wall_left = rect.right - wall_w
    right_pillar = pygame.Rect(wall_left - pillar_w, 0, pillar_w, belt_bottom)
    opening = pygame.Rect(right_pillar.left - opening_w, 0, opening_w, rect.top)
    left_pillar = pygame.Rect(opening.left - pillar_w, 0, pillar_w, belt_bottom)
    return {
        "belt_h": belt_h,
        "wall_w": wall_w,
        "wall_left": wall_left,
        "left_pillar": left_pillar,
        "opening": opening,
        "right_pillar": right_pillar,
    }


def _draw_treadmill(screen: pygame.Surface, rect: pygame.Rect, phase: float = 0.0) -> None:
    """Draw fixed, rotating poles with a chain of links looping around them."""
    layout = _treadmill_layout(rect)
    belt_h = layout["belt_h"]

    belt_black = (17, 10, 5)
    pole_gray = (170, 170, 170)
    pole_dark = (125, 125, 125)
    spoke_color = (70, 70, 70)
    chain_color = (150, 150, 150)

    belt = pygame.Rect(rect.left, rect.top, layout["right_pillar"].left - rect.left, belt_h)
    pygame.draw.rect(screen, belt_black, belt)

    link_h = max(2, belt_h // 8)
    link_len = max(4, belt_h // 4)
    path_r = belt_h / 2 - link_h / 2
    pole_r = max(4, round(path_r * 0.8))
    center_y = belt.centery
    left_x = belt.left + belt_h / 2
    right_x = belt.right - belt_h / 2

    spacing = belt_h * 1.55
    pole_count = max(2, round((right_x - left_x) / spacing) + 1)
    spin = phase / path_r
    for index in range(pole_count):
        x = round(left_x + (right_x - left_x) * index / (pole_count - 1))
        pygame.draw.circle(screen, pole_gray, (x, center_y), pole_r)
        pygame.draw.circle(screen, pole_dark, (x, center_y), max(2, pole_r // 2))
        for offset in (0.0, math.pi):
            angle = spin + offset
            end = (
                round(x + math.cos(angle) * pole_r * 0.85),
                round(center_y + math.sin(angle) * pole_r * 0.85),
            )
            pygame.draw.line(screen, spoke_color, (x, center_y), end, max(1, pole_r // 5))
        pygame.draw.circle(screen, pole_gray, (x, center_y), max(1, pole_r // 4))

    def draw_link(x: float, y: float, angle: float) -> None:
        half_length = link_len / 2
        half_height = link_h / 2
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        corners = []
        for along, across in (
            (-half_length, -half_height),
            (half_length, -half_height),
            (half_length, half_height),
            (-half_length, half_height),
        ):
            corners.append((
                round(x + along * cos_a - across * sin_a),
                round(y + along * sin_a + across * cos_a),
            ))
        pygame.draw.polygon(screen, chain_color, corners)

    straight = right_x - left_x
    arc = math.pi * path_r
    loop = 2 * straight + 2 * arc
    link_count = max(8, round(loop / (link_len * 2)))
    pitch = loop / link_count
    for index in range(link_count):
        distance = (phase + index * pitch) % loop
        if distance < straight:
            draw_link(left_x + distance, center_y - path_r, 0.0)
        elif distance < straight + arc:
            theta = -math.pi / 2 + (distance - straight) / path_r
            draw_link(
                right_x + math.cos(theta) * path_r,
                center_y + math.sin(theta) * path_r,
                theta + math.pi / 2,
            )
        elif distance < 2 * straight + arc:
            offset = distance - straight - arc
            draw_link(right_x - offset, center_y + path_r, math.pi)
        else:
            theta = math.pi / 2 + (distance - 2 * straight - arc) / path_r
            draw_link(
                left_x + math.cos(theta) * path_r,
                center_y + math.sin(theta) * path_r,
                theta + math.pi / 2,
            )


def _draw_house_behind_treadmill(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw only the left pillar and black box behind the treadmill and horses."""
    layout = _treadmill_layout(rect)
    orange = (221, 120, 45)
    belt_black = (17, 10, 5)

    pygame.draw.rect(screen, orange, layout["left_pillar"])
    pygame.draw.rect(screen, belt_black, layout["opening"])


def _draw_house_front(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw the entire pink wall section, right pillar, and corner piece in front of the horses."""
    layout = _treadmill_layout(rect)
    belt_bottom = rect.top + layout["belt_h"]
    wall_left = layout["wall_left"]

    orange = (221, 120, 45)
    wall_pink = (200, 60, 90)

    # Upper/main pink wall section
    pygame.draw.polygon(
        screen,
        wall_pink,
        [
            (wall_left, 0),
            (rect.right, 0),
            (rect.right, belt_bottom - layout["wall_w"]),
            (wall_left, belt_bottom),
        ],
    )
    # Right pillar
    pygame.draw.rect(screen, orange, layout["right_pillar"])

    # Bottom-right angled corner roof piece
    corner_poly = [
        (wall_left, belt_bottom),
        (rect.right, belt_bottom),
        (rect.right, belt_bottom - layout["wall_w"]),
    ]
    pygame.draw.polygon(screen, (132, 43, 57), corner_poly)


def _horse_on_treadmill(
    rag: ragdoll.Ragdoll, treadmill: pygame.Rect, tolerance: int
) -> bool:
    bounds = rag.race.rect()
    return (
        bounds.right > treadmill.left
        and bounds.left < treadmill.right
        and abs(bounds.bottom - _treadmill_belt_y(treadmill)) <= tolerance
    )


def _apply_treadmill_force(
    rag: ragdoll.Ragdoll,
    acceleration: float = 8.0,
    max_speed: float = 2.5,
) -> None:
    """Apply a rightward belt force while capping forward speed."""
    for part in rag.parts:
        body = part.native
        if body.linearVelocity.x < max_speed:
            body.ApplyForce(
                force=(body.mass * acceleration, 0),
                point=body.worldCenter,
                wake=True,
            )


def run_scale_house(horses: list, on_sold=None) -> None:
    """Let the player select and weigh caught horses in the van."""
    screen = pygame.display.get_surface()
    if screen is None:
        raise RuntimeError("The display must be initialized before entering the scale house.")

    pygame.display.set_caption("Glue")
    clock = pygame.time.Clock()
    scale_art = pygame.Surface((229, 148), pygame.SRCALPHA)
    van_scale = min(
        screen.get_width() * 0.58 / 358,
        screen.get_height() * 0.46 / 170,
    )
    van_size = (max(1, round(358 * van_scale)), max(1, round(170 * van_scale)))
    van_margin = max(12, screen.get_width() // 40)
    van_rect = pygame.Rect(
        screen.get_width() - van_size[0] - van_margin,
        screen.get_height() - van_size[1],
        *van_size,
    )
    treadmill_rect = pygame.Rect(
        screen.get_width() // 2,
        van_rect.top - max(C.s(64), screen.get_height() // 14),
        screen.get_width() - screen.get_width() // 2,
        max(C.s(64), screen.get_height() // 14),
    )
    
    layout = _treadmill_layout(treadmill_rect)
    house_left = layout["right_pillar"].right

    van_scale_x = van_rect.width / 358
    van_scale_y = van_rect.height / 170
    van_area_top = van_rect.top + round(8 * van_scale_y)
    van_floor_y = van_rect.top + round(134 * van_scale_y)
    van_area = pygame.Rect(
        van_rect.left + round(8 * van_scale_x),
        van_area_top,
        round(342 * van_scale_x),
        van_floor_y + 4 - van_area_top,
    )
    space = ragdoll.create_space()
    van_floor = van_area.bottom - 4
    van_wall_top = van_area.top
    space.add_edge((van_area.left, van_floor), (van_area.right, van_floor), friction=2.5)
    space.add_edge((van_area.left, van_floor), (van_area.left, van_wall_top), friction=2.5)
    space.add_edge((van_area.right, van_floor), (van_area.right, van_wall_top), friction=2.5)
    treadmill_floor_y = _treadmill_belt_y(treadmill_rect)
    space.add_edge(
        (treadmill_rect.left, treadmill_floor_y),
        (treadmill_rect.right, treadmill_floor_y),
        friction=0,
    )
    scale_factor = min(
        screen.get_width() / (2 * scale_art.get_width()),
        screen.get_height() / (2 * scale_art.get_height()),
    )
    scale_top = C.s(55)
    scale_floor_y = scale_top + round(122 * scale_factor)
    scale_platform = pygame.Rect(
        round(62 * scale_factor),
        scale_floor_y,
        round((173 - 62) * scale_factor),
        max(1, round(8 * scale_factor)),
    )
    space.add_edge(
        (round(62 * scale_factor), scale_floor_y),
        (round(173 * scale_factor), scale_floor_y),
        friction=2.5,
    )
    rags: list[ragdoll.Ragdoll] = []
    for horse in horses:
        race, parts = ragdoll.build_ragdoll(space, len(rags), van_area, horse.traits)
        van_rag = ragdoll.Ragdoll(horse, race, parts, zone="van")
        
        # If the horse is dead, ensure its joints are completely floppy in the scale house too
        if horse.traits.get("dead", False):
            for leg in van_rag.race.legs:
                joint = leg.motor
                joint.enableMotor = False
                joint.enableLimit = False
                joint.motorSpeed = 0.0
                joint.maxMotorTorque = 0.0
                if hasattr(joint, "lower_limit"):
                    joint.lower_limit = -float("inf")
                if hasattr(joint, "upper_limit"):
                    joint.upper_limit = float("inf")
            for part in van_rag.parts:
                body = getattr(part, "native", None)
                if body is not None:
                    body.awake = True

        rags.append(van_rag)

    drag: dict = {"rag": None, "ox": 0.0, "oy": 0.0}
    physics_accumulator = 0.0
    belt_phase = 0.0
    sale_popup = ""
    sale_popup_until = 0

    while True:
        dt = min(clock.tick(C.FPS_WORLD) / 1000.0, 0.033)
        belt_phase += dt * 75
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if drag["rag"] is not None:
                    ragdoll.set_drag_collisions(drag["rag"], enabled=True)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if drag["rag"] is not None:
                        ragdoll.freeze(drag["rag"].race)
                        ragdoll.set_drag_collisions(drag["rag"], enabled=True)
                    return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and drag["rag"] is None:
                hit = next(
                    (rag for rag in reversed(rags) if rag.race.rect().collidepoint(event.pos)),
                    None,
                )
                if hit is not None:
                    torso = hit.race.torso
                    drag["rag"] = hit
                    drag["ox"] = torso.position.x - event.pos[0]
                    drag["oy"] = torso.position.y - event.pos[1]
                    ragdoll.freeze(hit.race)
                    ragdoll.set_drag_collisions(hit, enabled=False)
                    physics_accumulator = 0.0
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and drag["rag"] is not None:
                hit = drag["rag"]
                ragdoll.freeze(hit.race)
                ragdoll.set_drag_collisions(hit, enabled=True)
                drag["rag"] = None
                physics_accumulator = 0.0

        if drag["rag"] is not None:
            torso = drag["rag"].race.torso
            ragdoll.move_horse_by(
                drag["rag"].race,
                mouse_pos[0] + drag["ox"] - torso.position.x,
                mouse_pos[1] + drag["oy"] - torso.position.y,
            )
        for rag in rags:
            if not rag.world_horse.traits.get("dead", False):
                rag.race.update(dt, is_dragged=(rag is drag["rag"]))

        physics_accumulator += dt
        while physics_accumulator >= C.PHYSICS_STEP:
            for rag in rags:
                if rag is not drag["rag"] and _horse_on_treadmill(
                    rag, treadmill_rect, max(14, treadmill_rect.height // 3)
                ):
                    rag._rode_treadmill = True
                    _apply_treadmill_force(rag)
            space.step(C.PHYSICS_STEP)
            physics_accumulator -= C.PHYSICS_STEP

        for rag in rags[:]:
            if not getattr(rag, "_rode_treadmill", False) or rag.race.rect().left < house_left:
                continue
            payout = _sale_payout(_horse_weight(rag))
            for part in rag.parts:
                space.world.DestroyBody(part.native)
            rags.remove(rag)
            if rag.world_horse in horses:
                horses.remove(rag.world_horse)
            if on_sold is not None:
                on_sold(rag.world_horse, payout)
            else:
                track.player_money += payout
            sale_popup = f"+${payout}"
            sale_popup_until = pygame.time.get_ticks() + 2500

        on_scale = [
            rag for rag in rags
            if rag is not drag["rag"] and _horse_on_scale(
                rag, scale_platform, max(12, round(6 * scale_factor))
            )
        ]
        total_weight = sum(_horse_weight(rag) for rag in on_scale)

        screen.fill(BACKGROUND)
        
        # 1. Background elements behind treadmill & horses
        _draw_house_behind_treadmill(screen, treadmill_rect)

        # 2. Treadmill belt
        _draw_treadmill(screen, treadmill_rect, belt_phase)
        
        treadmill_label_font = get_font(max(18, C.s(24)), bold=True)
        treadmill_label = treadmill_label_font.render(
            "5 dollars for 100 lbs",
            True,
            tuple(channel * 2 // 3 for channel in BACKGROUND),
        )
        treadmill_label_rect = treadmill_label.get_rect(
            bottomright=(layout["left_pillar"].left - max(16, C.s(20)), treadmill_rect.top - max(100, C.s(120)))
        )
        screen.blit(treadmill_label, treadmill_label_rect)
        
        scale_art.fill((0, 0, 0, 0))
        pygame.draw.rect(scale_art, (55, 53, 51), (12, 3, 214, 36))
        pygame.draw.rect(scale_art, (205, 207, 201), (15, 6, 208, 29))
        pygame.draw.rect(scale_art, (239, 238, 224), (18, 8, 202, 15))
        scale_left, scale_right = 18, 220
        for tick in range(31):
            x = scale_left + (scale_right - scale_left) * tick // 30
            major = tick % 10 == 0
            pygame.draw.line(scale_art, (45, 45, 43), (x, 24), (x, 31 if major else 28), 1)

        pygame.draw.rect(scale_art, (158, 158, 154), (106, 39, 20, 84))
        pygame.draw.rect(scale_art, (41, 39, 38), (62, 122, 111, 8))
        pygame.draw.rect(scale_art, (152, 151, 145), (70, 130, 95, 8))

        if on_scale:
            marker_x = scale_left + int(
                (scale_right - scale_left) * min(total_weight, 3000) / 3000
            )
            pygame.draw.line(scale_art, (179, 33, 42), (marker_x, 23), (marker_x, 32), 2)

        scale_size = (
            max(1, int(scale_art.get_width() * scale_factor)),
            max(1, int(scale_art.get_height() * scale_factor)),
        )
        screen.blit(pygame.transform.scale(scale_art, scale_size), (0, scale_top))

        label_font = pygame.font.SysFont("Arial", max(10, round(7 * scale_factor)), bold=True)
        for label, x in (("1000", 81), ("2000", 146), ("3000", 199)):
            text = label_font.render(label, True, (30, 30, 29))
            screen.blit(
                text,
                text.get_rect(center=(round(x * scale_factor), scale_top + round(17 * scale_factor))),
            )
        if on_scale:
            weight_font = pygame.font.SysFont(
                "Arial", max(16, round(10 * scale_factor)), bold=True
            )
            weight_text = weight_font.render(
                f"Weight: {total_weight:,} lb", True, (255, 245, 225)
            )
            screen.blit(
                weight_text,
                (min(scale_size[0] + max(12, round(8 * scale_factor)),
                     screen.get_width() - weight_text.get_width() - 12),
                 scale_top + max(12, round(10 * scale_factor))),
            )

        _draw_van(screen, van_rect)
        
        # 3. Draw horses in the middle layer
        ordered = [rag.race for rag in rags if rag is not drag["rag"]]
        if drag["rag"] is not None:
            ordered.append(drag["rag"].race)
        draw_horses(screen, ordered)

        # 4. Draw the full pink wall section, right pillar, and bottom-right corner in front of the horses
        _draw_house_front(screen, treadmill_rect)

        track.draw_player_money(screen, get_font(C.s(28), bold=True))
        if pygame.time.get_ticks() < sale_popup_until:
            popup_font = get_font(max(24, C.s(40)), bold=True)
            popup = popup_font.render(f"Sold horse! {sale_popup}", True, (255, 238, 120))
            popup_rect = popup.get_rect(center=(screen.get_width() // 2, C.s(70)))
            popup_bg = popup_rect.inflate(C.s(36), C.s(22))
            pygame.draw.rect(screen, (55, 35, 29), popup_bg, border_radius=C.s(10))
            pygame.draw.rect(screen, C.GOLD, popup_bg, max(2, C.s(3)), border_radius=C.s(10))
            screen.blit(popup, popup_rect)
        pygame.display.flip()