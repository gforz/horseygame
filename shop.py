"""shop.py — Lasso-Mart (Horse-Mart) shop interior scene."""

import math
import pygame

import constants as C
import ragdoll
import track
from methods import draw_horses, get_font

# Module-level persistence for hay bought in the van (when no van instance passed)
_bought_hay: list[dict] = []


def sync_hay(*lists) -> list[dict]:
    """Merge hay dicts from any lists into the one shared store and return it.

    The shop and the farm both use this store, so a hay dict changed in the
    farm (location "farm" / "van") is the exact same dict the shop reads.
    """
    for lst in lists:
        if lst is None or lst is _bought_hay:
            continue
        for item in lst:
            if not any(item is known for known in _bought_hay):
                _bought_hay.append(item)
    return _bought_hay

# Persistent stock of counter hay: 8 sheaves (4 in back row, 4 in front row)
# They do not respawn once bought.
_shop_counter_hay = [
    {"id": 0, "u": 0.20, "v": 0.72, "bought": False},
    {"id": 1, "u": 0.50, "v": 0.72, "bought": False},
    {"id": 2, "u": 0.80, "v": 0.72, "bought": False},
    {"id": 3, "u": 0.20, "v": 0.30, "bought": False},
    {"id": 4, "u": 0.50, "v": 0.30, "bought": False},
    {"id": 5, "u": 0.80, "v": 0.30, "bought": False},
]

# Pixel art map for hay sheaf matching the reference screenshot
HAY_PIXEL_MAP = [
    "..Y...Y...Y..",
    ".YY...YY..YY.",
    ".YYYYYYYYYYY.",
    "..YYYYYYYYY..",
    "...YYYYYYY...",
    "....YYYYY....",
    "....YYYYY....",
    "....YYYYY....",
    "....YYYYY....",
    "...YYYYYYY...",
    "..YYYYYYYYY..",
    ".YYYYYYYYYYY.",
    ".Y..YY.YY..Y.",
    "Y...Y...Y...Y",
]

_hay_sprite_cache: dict[int, pygame.Surface] = {}


def get_pixel_hay_sprite(scale: int) -> pygame.Surface:
    """Return a crisp, nearest-neighbor pixelated hay sprite."""
    scale = max(2, scale)
    if scale in _hay_sprite_cache:
        return _hay_sprite_cache[scale]

    ph = len(HAY_PIXEL_MAP)
    pw = len(HAY_PIXEL_MAP[0])
    base = pygame.Surface((pw, ph), pygame.SRCALPHA)

    for y, row in enumerate(HAY_PIXEL_MAP):
        for x, ch in enumerate(row):
            if ch == "Y":
                if x in (0, pw - 1) or y == ph - 1:
                    color = (195, 195, 30)
                elif x in (pw // 2, pw // 2 - 1) and 4 <= y <= 8:
                    color = (250, 255, 130)
                else:
                    color = (228, 236, 63)
                base.set_at((x, y), color)

    scaled = pygame.transform.scale(base, (pw * scale, ph * scale))
    _hay_sprite_cache[scale] = scaled
    return scaled


_lasso_sprite_cache: dict[int, pygame.Surface] = {}
LASSO_W, LASSO_H = 22, 27
LASSO_ANCHOR = (7, 1)  # where the peg sits inside the sprite


def get_pixel_lasso_sprite(scale: int) -> pygame.Surface:
    """Return a chunky, nearest-neighbor pixelated lasso sprite."""
    scale = max(1, scale)
    if scale in _lasso_sprite_cache:
        return _lasso_sprite_cache[scale]

    base = pygame.Surface((LASSO_W, LASSO_H), pygame.SRCALPHA)
    dark = (96, 52, 22)
    mid = (170, 110, 55)
    ax, ay = LASSO_ANCHOR

    def draw_rope(pts: list, closed: bool = False) -> None:
        ipts = [(int(round(x)), int(round(y))) for x, y in pts]
        pygame.draw.lines(base, dark, closed, ipts, 1)
        # lighter pixels along the rope give a twisted look
        for i, p in enumerate(ipts):
            if i % 3 == 0:
                base.set_at(p, mid)

    ang = -0.35
    ca, sa = math.cos(ang), math.sin(ang)
    cx, cy = ax + 3, ay + 9
    rx, ry = 8.0, 5.0

    def loop_pt(t: float) -> tuple[float, float]:
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        return (cx + ex * ca - ey * sa, cy + ex * sa + ey * ca)

    # Loop
    draw_rope([loop_pt(i / 40 * math.tau) for i in range(40)], closed=True)

    # Strand from the peg down to the loop
    draw_rope([(ax, ay), (ax + 1, ay + 3), loop_pt(-math.pi / 2)])

    # Tail curling out of the loop
    start = loop_pt(math.pi * 0.85)
    ctrl = (start[0] - 3, start[1] + 6)
    end = (start[0] - 1, start[1] + 10)
    tail = []
    for i in range(13):
        u = i / 12
        tail.append((
            (1 - u) ** 2 * start[0] + 2 * (1 - u) * u * ctrl[0] + u**2 * end[0],
            (1 - u) ** 2 * start[1] + 2 * (1 - u) * u * ctrl[1] + u**2 * end[1],
        ))
    draw_rope(tail)

    scaled = pygame.transform.scale(base, (LASSO_W * scale, LASSO_H * scale))
    _lasso_sprite_cache[scale] = scaled
    return scaled


def _draw_lasso(surf: pygame.Surface, peg_x: int, peg_y: int, scale: int) -> None:
    """Blit the pixelated lasso so its peg anchor lands on (peg_x, peg_y)."""
    sprite = get_pixel_lasso_sprite(scale)
    ax, ay = LASSO_ANCHOR
    surf.blit(sprite, (peg_x - ax * max(1, scale), peg_y - ay * max(1, scale)))


def _in_van(item: dict) -> bool:
    """Hay left loose on the farm (location == "farm") is not in the van."""
    return item.get("location", "van") != "farm"


def run_shop(van=None) -> None:
    """Run the Lasso-Mart shop interior loop."""
    screen = pygame.display.get_surface()
    if screen is None:
        raise RuntimeError("The display must be initialized before entering the shop.")

    pygame.display.set_caption("Horse-Mart")
    clock = pygame.time.Clock()

    # Room Colors
    WALL_BG = (105, 68, 28)
    FLOOR_BG = (75, 48, 18)
    PANEL_BG = (26, 101, 10)
    PANEL_BORDER = (18, 70, 8)
    HOVER_BG = (42, 142, 28)
    TEXT_WHITE = (255, 255, 255)
    GOLD = (255, 215, 0)

    # Van colors exactly matching farm.py
    VAN_BORDER = (130, 200, 240)
    VAN_FILL = (255, 255, 255)
    VAN_BED = (150, 150, 160)
    WHEEL = (20, 20, 20)
    HUB = (200, 200, 205)

    # Van inventory and horses
    van_horses = van.inventory if (van and hasattr(van, "inventory")) else []
    if van is not None and hasattr(van, "hay_items"):
        van_hay = sync_hay(van.hay_items)
        try:
            van.hay_items = van_hay  # van and shop now share one list
        except AttributeError:
            pass
    else:
        van_hay = _bought_hay

    # Screen dimensions & Layout geometry
    w, h = screen.get_size()
    floor_y = int(h * 0.48)

    # Lasso pegboard on the back wall
    pb_w = int(w * 0.13)
    pb_h = int(h * 0.24)
    pb_x = int(w * 0.28)
    pb_y = int(h * 0.14)
    lasso_board_rect = pygame.Rect(pb_x, pb_y, pb_w, pb_h)

    # Price list board on right wall
    board_w = int(w * 0.18)
    board_h = int(h * 0.24)
    board_x = int(w * 0.63)
    board_y = int(h * 0.14)
    board_rect = pygame.Rect(board_x, board_y, board_w, board_h)

    row_h = int(board_h * 0.38)
    row_pad = int(board_h * 0.08)
    hay_row_rect = pygame.Rect(board_x + 10, board_y + row_pad, board_w - 20, row_h)
    lasso_row_rect = pygame.Rect(
        board_x + 10, board_y + row_pad + row_h + int(board_h * 0.08), board_w - 20, row_h
    )

    # 3D Counter geometry sitting firmly on the floor
    fx1, fy_base = int(w * 0.20), int(h * 0.82)
    fx2 = int(w * 0.35)
    bx1, by_base = int(w * 0.40), int(h * 0.58)
    bx2 = int(w * 0.53)

    ch_front = int(h * 0.16)
    ch_back = int(h * 0.12)

    fl_top = (fx1, fy_base - ch_front)
    fr_top = (fx2, fy_base - ch_front)
    bl_top = (bx1, by_base - ch_back)
    br_top = (bx2, by_base - ch_back)

    fl_base = (fx1, fy_base)
    fr_base = (fx2, fy_base)
    br_base = (bx2, by_base)

    # Horse trailer / van on the bottom right (sized to accommodate physics ragdoll horses)
    van_w = int(w * 0.42)
    van_h = int(h * 0.40)
    van_x = int(w * 0.56)
    van_y = int(h * 0.54)

    border_t = max(6, int(van_h * (8 / 142)))
    van_fill_rect = pygame.Rect(
        van_x + border_t, van_y + border_t, van_w - border_t * 2, van_h - border_t * 2
    )
    van_drop_rect = pygame.Rect(van_x, van_y, van_w, van_h).inflate(20, 20)

    # Physics Space for horses in the van (just like in glue.py!)
    space = ragdoll.create_space()
    ragdoll.add_box_walls(space, van_fill_rect)
    space.add_edge((-1000, h - 4), (w + 1000, h - 4), friction=2.5)

    horse_rags: list[ragdoll.Ragdoll] = []
    for h_obj in van_horses:
        race, parts = ragdoll.build_ragdoll(space, len(horse_rags), van_fill_rect, h_obj.traits)
        v_rag = ragdoll.Ragdoll(h_obj, race, parts, zone="van")
        if h_obj.traits.get("dead", False):
            for leg in v_rag.race.legs:
                joint = leg.motor
                joint.enableMotor = False
                joint.enableLimit = False
                joint.motorSpeed = 0.0
                joint.maxMotorTorque = 0.0
                if hasattr(joint, "lower_limit"):
                    joint.lower_limit = -float("inf")
                if hasattr(joint, "upper_limit"):
                    joint.upper_limit = float("inf")
            for part in v_rag.parts:
                body = getattr(part, "native", None)
                if body is not None:
                    body.gravity_scale = 1.0
        horse_rags.append(v_rag)

    # Settle physics briefly so horses land nicely on the van floor
    for _ in range(30):
        space.step(C.PHYSICS_STEP)

    # Purchase feedback message
    message = ""
    message_until = 0

    # Dragging states
    # 1. Counter hay dragging
    dragged_sheaf = None
    counter_drag_pos = [0.0, 0.0]
    counter_drag_offset = [0, 0]

    # Return animation for counter sheaves
    anim_sheaf = None
    anim_from = [0.0, 0.0]
    anim_start_time = 0
    anim_duration = 260  # ms
    anim_pos = [0.0, 0.0]

    # 2. Bought hay dragging inside the van
    dragged_van_hay = None
    van_hay_drag_offset = [0, 0]

    # 3. Horse dragging inside the van (ragdoll physics)
    drag_horse = {"rag": None, "ox": 0.0, "oy": 0.0}
    physics_acc = 0.0

    while True:
        dt = min(clock.tick(C.FPS_WORLD) / 1000.0, 0.033)
        mouse_pos = pygame.mouse.get_pos()

        # Pixel hay sprite
        hay_scale = max(2, int(w / 330))
        hay_sprite = get_pixel_hay_sprite(hay_scale)
        hay_sw, hay_sh = hay_sprite.get_size()

        # Compute home positions for all remaining counter sheaves
        counter_sheaf_positions = {}
        for s in _shop_counter_hay:
            if not s["bought"]:
                u, v = s["u"], s["v"]
                front_x = fl_top[0] + (fr_top[0] - fl_top[0]) * u
                front_y = fl_top[1] + (fr_top[1] - fl_top[1]) * u
                back_x = bl_top[0] + (br_top[0] - bl_top[0]) * u
                back_y = bl_top[1] + (br_top[1] - bl_top[1]) * u
                hx = int(front_x + (back_x - front_x) * v)
                hy = int(front_y + (back_y - front_y) * v) - int(hay_sh * 0.3)
                counter_sheaf_positions[s["id"]] = (hx, hy)

        # Update smooth return animation for counter hay
        if anim_sheaf is not None:
            home_xy = counter_sheaf_positions.get(anim_sheaf["id"])
            if home_xy is not None:
                elapsed = pygame.time.get_ticks() - anim_start_time
                t = min(1.0, elapsed / float(anim_duration))
                ease = 1.0 - (1.0 - t) ** 3
                anim_pos[0] = anim_from[0] + (home_xy[0] - anim_from[0]) * ease
                anim_pos[1] = anim_from[1] + (home_xy[1] - anim_from[1]) * ease
                if t >= 1.0:
                    anim_sheaf = None
            else:
                anim_sheaf = None

        # Dragging ragdoll horse
        if drag_horse["rag"] is not None:
            torso = drag_horse["rag"].race.torso
            ragdoll.move_horse_by(
                drag_horse["rag"].race,
                mouse_pos[0] + drag_horse["ox"] - torso.position.x,
                mouse_pos[1] + drag_horse["oy"] - torso.position.y,
            )

        # Physics stepping for horses
        physics_acc += dt
        while physics_acc >= C.PHYSICS_STEP:
            space.step(C.PHYSICS_STEP)
            physics_acc -= C.PHYSICS_STEP

        for rag in horse_rags:
            if not rag.world_horse.traits.get("dead", False):
                rag.race.update(dt, is_dragged=(rag is drag_horse["rag"]))

        # Hit detection for hover cursor
        hover_sheaf = None
        for s_id, (hx, hy) in counter_sheaf_positions.items():
            if anim_sheaf and anim_sheaf["id"] == s_id:
                continue
            if math.hypot(mouse_pos[0] - hx, mouse_pos[1] - hy) <= max(hay_sw, hay_sh) * 0.8:
                hover_sheaf = s_id
                break

        hover_van_hay = False
        for item in van_hay:
            if not _in_van(item):
                continue
            bx = van_fill_rect.left + int(item["rel_x"] * van_fill_rect.width)
            by = van_fill_rect.top + int(item["rel_y"] * van_fill_rect.height)
            if math.hypot(mouse_pos[0] - bx, mouse_pos[1] - by) <= max(hay_sw, hay_sh) * 0.8:
                hover_van_hay = True
                break

        hover_horse = any(
            rag.race.rect().collidepoint(mouse_pos) for rag in horse_rags
        )

        hovering_interactive = (
            hover_sheaf is not None
            or hover_van_hay
            or hover_horse
            or dragged_sheaf is not None
            or dragged_van_hay is not None
            or drag_horse["rag"] is not None
            or lasso_row_rect.collidepoint(mouse_pos)
            or lasso_board_rect.collidepoint(mouse_pos)
        )

        try:
            if hovering_interactive:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try:
                    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                except Exception:
                    pass
                if drag_horse["rag"] is not None:
                    ragdoll.set_drag_collisions(drag_horse["rag"], enabled=True)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    try:
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                    except Exception:
                        pass
                    if drag_horse["rag"] is not None:
                        ragdoll.freeze(drag_horse["rag"].race)
                        ragdoll.set_drag_collisions(drag_horse["rag"], enabled=True)
                    return

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Check if clicking any available counter hay sheaf
                clicked_sheaf = None
                for s in _shop_counter_hay:
                    if not s["bought"] and s["id"] in counter_sheaf_positions:
                        if anim_sheaf and anim_sheaf["id"] == s["id"]:
                            continue
                        hx, hy = counter_sheaf_positions[s["id"]]
                        if math.hypot(event.pos[0] - hx, event.pos[1] - hy) <= max(hay_sw, hay_sh) * 0.9:
                            clicked_sheaf = s
                            counter_drag_pos = [float(hx), float(hy)]
                            counter_drag_offset = [hx - event.pos[0], hy - event.pos[1]]
                            break

                if clicked_sheaf is not None:
                    dragged_sheaf = clicked_sheaf
                    anim_sheaf = None
                else:
                    # 2. Check if clicking a hay sheaf already in the van
                    clicked_van_item = None
                    for item in reversed(van_hay):
                        if not _in_van(item):
                            continue
                        bx = van_fill_rect.left + int(item["rel_x"] * van_fill_rect.width)
                        by = van_fill_rect.top + int(item["rel_y"] * van_fill_rect.height)
                        if math.hypot(event.pos[0] - bx, event.pos[1] - by) <= max(hay_sw, hay_sh) * 0.9:
                            clicked_van_item = item
                            van_hay_drag_offset = [bx - event.pos[0], by - event.pos[1]]
                            break

                    if clicked_van_item is not None:
                        dragged_van_hay = clicked_van_item
                    else:
                        # 3. Check if clicking a horse in the van (ragdoll grab)
                        hit_rag = next(
                            (rag for rag in reversed(horse_rags) if rag.race.rect().collidepoint(event.pos)),
                            None,
                        )
                        if hit_rag is not None:
                            torso = hit_rag.race.torso
                            drag_horse["rag"] = hit_rag
                            drag_horse["ox"] = torso.position.x - event.pos[0]
                            drag_horse["oy"] = torso.position.y - event.pos[1]
                            ragdoll.freeze(hit_rag.race)
                            ragdoll.set_drag_collisions(hit_rag, enabled=False)
                            physics_acc = 0.0
                        elif lasso_row_rect.collidepoint(event.pos) or lasso_board_rect.collidepoint(
                            event.pos
                        ):
                            if track.player_money >= 65:
                                track.player_money -= 65
                                message = "Purchased Lasso!"
                                message_until = pygame.time.get_ticks() + 2000
                            else:
                                message = "Not enough money!"
                                message_until = pygame.time.get_ticks() + 2000

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # Dropping a counter sheaf
                if dragged_sheaf is not None:
                    drop_x = event.pos[0] + counter_drag_offset[0]
                    drop_y = event.pos[1] + counter_drag_offset[1]
                    s = dragged_sheaf
                    dragged_sheaf = None

                    # Check if dropped inside the van
                    if van_drop_rect.collidepoint((drop_x, drop_y)):
                        if track.player_money >= 5:
                            track.player_money -= 5
                            message = "Purchased Hay!"
                            message_until = pygame.time.get_ticks() + 2000

                            # Mark this specific counter sheaf as bought (will NOT respawn)
                            s["bought"] = True

                            # Store inside van
                            rel_x = max(
                                0.08,
                                min(
                                    0.92,
                                    (drop_x - van_fill_rect.left)
                                    / float(max(1, van_fill_rect.width)),
                                ),
                            )
                            rel_y = max(
                                0.20,
                                min(
                                    0.88,
                                    (drop_y - van_fill_rect.top)
                                    / float(max(1, van_fill_rect.height)),
                                ),
                            )
                            # One shared dict, so the farm and shop always see the same hay
                            new_hay = {"rel_x": rel_x, "rel_y": rel_y, "location": "van"}
                            van_hay.append(new_hay)
                            if van_hay is not _bought_hay:
                                _bought_hay.append(new_hay)
                        else:
                            message = "Not enough money!"
                            message_until = pygame.time.get_ticks() + 2000
                            anim_sheaf = s
                            anim_from = [drop_x, drop_y]
                            anim_start_time = pygame.time.get_ticks()
                    else:
                        anim_sheaf = s
                        anim_from = [drop_x, drop_y]
                        anim_start_time = pygame.time.get_ticks()

                # Dropping a van hay item
                if dragged_van_hay is not None:
                    dragged_van_hay = None

                # Dropping a ragdoll horse
                if drag_horse["rag"] is not None:
                    hit_rag = drag_horse["rag"]
                    ragdoll.freeze(hit_rag.race)
                    ragdoll.set_drag_collisions(hit_rag, enabled=True)
                    drag_horse["rag"] = None
                    physics_acc = 0.0

            if event.type == pygame.MOUSEMOTION:
                if dragged_sheaf is not None:
                    counter_drag_pos[0] = event.pos[0] + counter_drag_offset[0]
                    counter_drag_pos[1] = event.pos[1] + counter_drag_offset[1]

                if dragged_van_hay is not None:
                    tx = event.pos[0] + van_hay_drag_offset[0]
                    ty = event.pos[1] + van_hay_drag_offset[1]
                    margin_x = hay_sw // 2
                    margin_y = hay_sh // 2
                    tx = max(van_fill_rect.left + margin_x, min(van_fill_rect.right - margin_x, tx))
                    ty = max(van_fill_rect.top + margin_y, min(van_fill_rect.bottom - margin_y, ty))
                    dragged_van_hay["rel_x"] = (tx - van_fill_rect.left) / float(max(1, van_fill_rect.width))
                    dragged_van_hay["rel_y"] = (ty - van_fill_rect.top) / float(max(1, van_fill_rect.height))

        # --- DRAWING ---
        # 1. Background wall and floor
        screen.fill(WALL_BG)
        pygame.draw.rect(screen, FLOOR_BG, (0, floor_y, w, h - floor_y))

        # Vertical wood planks on wall
        plank_w = max(18, int(w * 0.026))
        for px in range(0, w, plank_w):
            pygame.draw.line(screen, (70, 44, 16), (px, 0), (px, floor_y), 1)
            pygame.draw.line(screen, (135, 90, 40), (px + 1, 0), (px + 1, floor_y), 1)

        # Baseboard trim separating wall and floor
        baseboard_h = max(6, int(h * 0.012))
        pygame.draw.rect(
            screen, (120, 78, 30), (0, floor_y - baseboard_h // 2, w, baseboard_h)
        )
        pygame.draw.line(
            screen,
            (150, 100, 42),
            (0, floor_y - baseboard_h // 2),
            (w, floor_y - baseboard_h // 2),
            2,
        )
        pygame.draw.line(
            screen,
            (55, 35, 12),
            (0, floor_y + baseboard_h // 2),
            (w, floor_y + baseboard_h // 2),
            2,
        )

        # 2. Title: "Horse-Mart" retro purple outline style at top center
        title_font = get_font(C.s(42), bold=True)
        title_str = "Horse-Mart"
        title_outline_color = (185, 60, 215)
        title_inner_color = (95, 30, 105)
        title_cy = C.s(38)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            t_surf = title_font.render(title_str, True, title_outline_color)
            screen.blit(t_surf, t_surf.get_rect(center=(w // 2 + dx, title_cy + dy)))
        t_in = title_font.render(title_str, True, title_inner_color)
        screen.blit(t_in, t_in.get_rect(center=(w // 2, title_cy)))

        # 3. Money display (top left) — standard implementation from track/world
        track.draw_player_money(screen, get_font(C.s(28), bold=True))

        # 4. Lasso pegboard on the wall
        pygame.draw.rect(screen, (142, 248, 145), lasso_board_rect)
        if lasso_board_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (200, 255, 200), lasso_board_rect, max(3, int(w * 0.004)))
        else:
            pygame.draw.rect(screen, (100, 205, 105), lasso_board_rect, max(2, int(w * 0.003)))

        # 4 peg crosses (+) — gray like the reference
        peg_coords = [
            (pb_x + int(pb_w * 0.30), pb_y + int(pb_h * 0.14)),
            (pb_x + int(pb_w * 0.72), pb_y + int(pb_h * 0.14)),
            (pb_x + int(pb_w * 0.30), pb_y + int(pb_h * 0.58)),
            (pb_x + int(pb_w * 0.74), pb_y + int(pb_h * 0.66)),
        ]
        for px, py in peg_coords:
            arm = max(2, int(pb_w * 0.05))
            pygame.draw.line(screen, (120, 125, 125), (px - arm, py), (px + arm, py), 2)
            pygame.draw.line(screen, (120, 125, 125), (px, py - arm), (px, py + arm), 2)

        # Three lassos hang on the board, the fourth peg stays empty
        for px, py in peg_coords[:3]:
            _draw_lasso(screen, px, py, max(2, round(pb_w * 0.012)))

        # 5. Price list board on right wall
        pygame.draw.rect(screen, PANEL_BG, board_rect, border_radius=6)
        pygame.draw.rect(screen, PANEL_BORDER, board_rect, 3, border_radius=6)

        item_font = get_font(C.s(24), bold=True)

        hay_text = item_font.render("Hay $5", True, TEXT_WHITE)

        lasso_text = item_font.render("Lasso $65", True, TEXT_WHITE)

        # Hover state for Lasso row
        if lasso_row_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, HOVER_BG, lasso_row_rect, border_radius=4)

        screen.blit(hay_text, hay_text.get_rect(center=hay_row_rect.center))
        screen.blit(lasso_text, lasso_text.get_rect(center=lasso_row_rect.center))

        # 6. Angled wooden counter desk sitting firmly on the floor in 3D perspective
        # Side face (right)
        counter_side_pts = [fr_top, br_top, br_base, fr_base]
        pygame.draw.polygon(screen, (85, 48, 16), counter_side_pts)
        pygame.draw.polygon(screen, (115, 65, 22), counter_side_pts, 2)

        # Front face
        counter_front_pts = [fl_top, fr_top, fr_base, fl_base]
        pygame.draw.polygon(screen, (125, 70, 25), counter_front_pts)
        pygame.draw.polygon(screen, (165, 95, 35), counter_front_pts, 2)

        # Top surface
        counter_top_pts = [fl_top, fr_top, br_top, bl_top]
        pygame.draw.polygon(screen, (145, 85, 30), counter_top_pts)
        pygame.draw.polygon(screen, (190, 115, 45), counter_top_pts, 2)

        # Draw remaining stationary hay sheaves on the counter
        for s in sorted(_shop_counter_hay, key=lambda sh: -sh["v"]):
            if not s["bought"]:
                if (dragged_sheaf and dragged_sheaf["id"] == s["id"]) or (
                    anim_sheaf and anim_sheaf["id"] == s["id"]
                ):
                    continue
                pos = counter_sheaf_positions.get(s["id"])
                if pos:
                    screen.blit(hay_sprite, hay_sprite.get_rect(center=pos))

        # 7. Horse trailer / van on the bottom right (exact farm.py colors and proportions)
        is_over_van = (dragged_sheaf is not None) and van_drop_rect.collidepoint(
            (counter_drag_pos[0], counter_drag_pos[1])
        )

        # Undercarriage bed between wheels
        bed_w = int(van_w * (130 / 358))
        bed_h = int(van_h * (32 / 142))
        bed_x = van_x + int(van_w * ((445 - 372) / 358))
        bed_y = van_y + van_h - int(bed_h * 0.4)
        pygame.draw.rect(screen, VAN_BED, (bed_x, bed_y, bed_w, bed_h))

        # Van body (border & fill)
        current_van_border = (255, 230, 80) if is_over_van else VAN_BORDER
        pygame.draw.rect(screen, current_van_border, (van_x, van_y, van_w, van_h))
        pygame.draw.rect(screen, VAN_FILL, van_fill_rect)

        # Wheels
        wheel_r = int(van_h * (22 / 142))
        hub_r = max(2, int(van_h * (7 / 142)))
        for frac in [(475 - 372) / 358, (535 - 372) / 358]:
            cx = van_x + int(van_w * frac)
            cy = van_y + van_h + int(wheel_r * 0.15)
            pygame.draw.circle(screen, WHEEL, (cx, cy), wheel_r)
            pygame.draw.circle(screen, HUB, (cx, cy), hub_r)

        # Draw horses inside the van using Box2D ragdoll physics (same as glue.py!)
        if horse_rags:
            ordered_horses = [rag.race for rag in horse_rags if rag is not drag_horse["rag"]]
            if drag_horse["rag"] is not None:
                ordered_horses.append(drag_horse["rag"].race)
            draw_horses(screen, ordered_horses)

        # Draw all bought hay sheaves that stay in the van
        for item in van_hay:
            if not _in_van(item):
                continue
            bx = van_fill_rect.left + int(item["rel_x"] * van_fill_rect.width)
            by = van_fill_rect.top + int(item["rel_y"] * van_fill_rect.height)
            if dragged_van_hay is item:
                shadow_w, shadow_h = int(hay_sw * 1.1), int(hay_sh * 0.3)
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), (0, 0, shadow_w, shadow_h))
                screen.blit(shadow_surf, (bx - shadow_w // 2, by + hay_sh // 2 + 4))
            screen.blit(hay_sprite, hay_sprite.get_rect(center=(bx, by)))

        # Drop prompt inside van when dragging hay
        if dragged_sheaf is not None:
            prompt_font = get_font(C.s(20), bold=True)
            prompt_surf = prompt_font.render(
                "Drop Hay Here!", True, (40, 160, 50) if is_over_van else (120, 170, 210)
            )
            screen.blit(
                prompt_surf,
                prompt_surf.get_rect(
                    center=(van_x + van_w // 2, van_y + int(van_h * 0.80))
                ),
            )

        # 8. Draw returning animated sheaf (if any)
        if anim_sheaf is not None:
            screen.blit(
                hay_sprite,
                hay_sprite.get_rect(center=(int(anim_pos[0]), int(anim_pos[1]))),
            )

        # 9. Draw currently dragged counter sheaf with shadow
        if dragged_sheaf is not None:
            shadow_w, shadow_h = int(hay_sw * 1.1), int(hay_sh * 0.3)
            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(
                shadow_surf, (0, 0, 0, 60), (0, 0, shadow_w, shadow_h)
            )
            screen.blit(
                shadow_surf,
                (
                    int(counter_drag_pos[0] - shadow_w // 2),
                    int(counter_drag_pos[1] + hay_sh // 2 + 6),
                ),
            )
            screen.blit(
                hay_sprite,
                hay_sprite.get_rect(
                    center=(int(counter_drag_pos[0]), int(counter_drag_pos[1]))
                ),
            )

        # 10. Purchase Popup Message
        if pygame.time.get_ticks() < message_until:
            msg_font = get_font(C.s(28), bold=True)
            msg_surf = msg_font.render(message, True, GOLD)
            msg_rect = msg_surf.get_rect(center=(w // 2, h - int(h * 0.16)))
            pygame.draw.rect(
                screen, (40, 20, 10), msg_rect.inflate(30, 16), border_radius=8
            )
            pygame.draw.rect(screen, GOLD, msg_rect.inflate(30, 16), 2, border_radius=8)
            screen.blit(msg_surf, msg_rect)

        pygame.display.flip()
