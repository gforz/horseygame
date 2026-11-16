"""shop.py — Lasso-Mart (Horse-Mart) shop interior scene.

Buy hay by dragging a sheaf from the counter into your van, and buy lassos off
the pegboard. Caught horses in the van are simulated as ragdolls, so you can
drag them around while you shop.
"""

import math

import pygame

from game import constants as C
from game import daytime
from game import state
from game.display import set_game_cursor, set_hand_cursor
from game.gfx.fonts import get_font
from game.gfx.horse_draw import draw_horses
from game.items import (
    get_pixel_hay_sprite,
    hay_in_van,
    hay_sprite_scale,
    sync_hay,
)
from game.scenes import shop_art
from game.scenes.shop_art import GOLD, Room
from game.sim import ragdoll
from game.sim.horse_care import kill_ragdoll
from game.ui import hud

# Counter hay: sheaves laid out on the counter (u across, v front-to-back).
_shop_counter_hay = [
    {"id": 0, "u": 0.20, "v": 0.72, "bought": False},
    {"id": 1, "u": 0.50, "v": 0.72, "bought": False},
    {"id": 2, "u": 0.80, "v": 0.72, "bought": False},
    {"id": 3, "u": 0.20, "v": 0.30, "bought": False},
    {"id": 4, "u": 0.50, "v": 0.30, "bought": False},
    {"id": 5, "u": 0.80, "v": 0.30, "bought": False},
]

# Lassos hanging on the pegboard.
_LASSO_DAILY_STOCK = 4
_lasso_stock = {"left": _LASSO_DAILY_STOCK}
_shop_stock_day: int | None = None


def _restock_shop() -> None:
    global _shop_stock_day
    if _shop_stock_day == daytime.day_index:
        return

    for sheaf in _shop_counter_hay:
        sheaf["bought"] = False
    _lasso_stock["left"] = _LASSO_DAILY_STOCK
    _shop_stock_day = daytime.day_index


def reset_shop() -> None:
    """Restore shop stock for a new playthrough."""
    global _shop_stock_day
    for sheaf in _shop_counter_hay:
        sheaf["bought"] = False
    _lasso_stock["left"] = _LASSO_DAILY_STOCK
    _shop_stock_day = None


def run_shop(van=None) -> None:
    """Run the Lasso-Mart shop interior loop."""
    screen = pygame.display.get_surface()
    if screen is None:
        raise RuntimeError("The display must be initialized before entering the shop.")

    _restock_shop()
    set_game_cursor()
    pygame.display.set_caption("Horse-Mart")
    clock = pygame.time.Clock()

    room = Room(*screen.get_size())

    # Van inventory and horses
    van_horses = van.inventory if (van and hasattr(van, "inventory")) else []
    if van is not None and hasattr(van, "hay_items"):
        van_hay = sync_hay(van.hay_items)
        try:
            van.hay_items = van_hay  # van and shop now share one list
        except AttributeError:
            pass
    else:
        van_hay = sync_hay()

    van_fill_rect = room.van_fill_rect
    van_drop_rect = room.van_drop_rect
    lasso_hit_rects = room.lasso_hit_rects
    lasso_pixel = room.lasso_pixel

    # Physics space for the horses in the van (just like in glue.py!)
    space = ragdoll.create_space()
    ragdoll.add_box_walls(space, van_fill_rect)
    space.add_edge((-1000, room.h - 4), (room.w + 1000, room.h - 4), friction=2.5)

    horse_rags: list[ragdoll.Ragdoll] = []
    for h_obj in van_horses:
        race, parts = ragdoll.build_ragdoll(space, len(horse_rags), van_fill_rect, h_obj.traits)
        v_rag = ragdoll.Ragdoll(h_obj, race, parts, zone="van")
        if h_obj.traits.get("dead", False):
            kill_ragdoll(v_rag, wake=False)
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
        hay_sprite = get_pixel_hay_sprite(hay_sprite_scale(room.w))
        hay_sw, hay_sh = hay_sprite.get_size()

        # Compute home positions for all remaining counter sheaves
        counter_sheaf_positions = {}
        for sheaf in _shop_counter_hay:
            if not sheaf["bought"]:
                counter_sheaf_positions[sheaf["id"]] = room.sheaf_home(
                    sheaf["u"], sheaf["v"], hay_sh
                )

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
            if not hay_in_van(item):
                continue
            bx = van_fill_rect.left + int(item["rel_x"] * van_fill_rect.width)
            by = van_fill_rect.top + int(item["rel_y"] * van_fill_rect.height)
            if math.hypot(mouse_pos[0] - bx, mouse_pos[1] - by) <= max(hay_sw, hay_sh) * 0.8:
                hover_van_hay = True
                break

        hover_horse = any(
            rag.race.rect().collidepoint(mouse_pos) for rag in horse_rags
        )

        hover_lasso = any(
            rect.collidepoint(mouse_pos)
            for rect in lasso_hit_rects[:_lasso_stock["left"]]
        )

        hovering_interactive = (
            hover_sheaf is not None
            or hover_van_hay
            or hover_horse
            or dragged_sheaf is not None
            or dragged_van_hay is not None
            or drag_horse["rag"] is not None
            or hover_lasso
        )

        if hovering_interactive:
            set_hand_cursor()
        else:
            set_game_cursor()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                set_game_cursor()
                if drag_horse["rag"] is not None:
                    ragdoll.set_drag_collisions(drag_horse["rag"], enabled=True)
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    set_game_cursor()
                    if drag_horse["rag"] is not None:
                        ragdoll.freeze(drag_horse["rag"].race)
                        ragdoll.set_drag_collisions(drag_horse["rag"], enabled=True)
                    return

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 1. Check if clicking any available counter hay sheaf
                clicked_sheaf = None
                for sheaf in _shop_counter_hay:
                    if sheaf["bought"] or sheaf["id"] not in counter_sheaf_positions:
                        continue
                    if anim_sheaf and anim_sheaf["id"] == sheaf["id"]:
                        continue
                    hx, hy = counter_sheaf_positions[sheaf["id"]]
                    if math.hypot(event.pos[0] - hx, event.pos[1] - hy) <= max(hay_sw, hay_sh) * 0.9:
                        clicked_sheaf = sheaf
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
                        if not hay_in_van(item):
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
                        elif any(rect.collidepoint(event.pos) for rect in lasso_hit_rects[:_lasso_stock["left"]]):
                            if _lasso_stock["left"] <= 0:
                                message = "Lassos are sold out!"
                                message_until = pygame.time.get_ticks() + 2000
                            elif state.player_money >= shop_art.LASSO_PRICE:
                                state.player_money -= shop_art.LASSO_PRICE
                                _lasso_stock["left"] -= 1
                                state.lasso_count += 1
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
                    sheaf = dragged_sheaf
                    dragged_sheaf = None

                    # Check if dropped inside the van
                    if van_drop_rect.collidepoint((drop_x, drop_y)):
                        if state.player_money >= shop_art.HAY_PRICE:
                            state.player_money -= shop_art.HAY_PRICE
                            message = "Purchased Hay!"
                            message_until = pygame.time.get_ticks() + 2000

                            # Mark this specific counter sheaf as bought (will NOT respawn)
                            sheaf["bought"] = True

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
                            van_hay.append(
                                {"rel_x": rel_x, "rel_y": rel_y, "location": "van"}
                            )
                        else:
                            message = "Not enough money!"
                            message_until = pygame.time.get_ticks() + 2000
                            anim_sheaf = sheaf
                            anim_from = [drop_x, drop_y]
                            anim_start_time = pygame.time.get_ticks()
                    else:
                        anim_sheaf = sheaf
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
        shop_art.draw_room(screen, room)
        shop_art.draw_title(screen, room)
        shop_art.draw_lasso_board(screen, room, lasso_pixel, _lasso_stock["left"], hover_lasso)
        shop_art.draw_price_board(screen, room, _lasso_stock["left"])
        shop_art.draw_counter(screen, room)

        # Stationary hay sheaves on the counter
        for sheaf in sorted(_shop_counter_hay, key=lambda sh: -sh["v"]):
            if sheaf["bought"]:
                continue
            if (dragged_sheaf and dragged_sheaf["id"] == sheaf["id"]) or (
                anim_sheaf and anim_sheaf["id"] == sheaf["id"]
            ):
                continue
            pos = counter_sheaf_positions.get(sheaf["id"])
            if pos:
                screen.blit(hay_sprite, hay_sprite.get_rect(center=pos))

        # Horse trailer on the bottom right
        is_over_van = (dragged_sheaf is not None) and van_drop_rect.collidepoint(
            (counter_drag_pos[0], counter_drag_pos[1])
        )
        shop_art.draw_van(screen, room, highlight=is_over_van)

        # Horses inside the van, simulated with Box2D ragdolls
        if horse_rags:
            ordered_horses = [rag.race for rag in horse_rags if rag is not drag_horse["rag"]]
            if drag_horse["rag"] is not None:
                ordered_horses.append(drag_horse["rag"].race)
            draw_horses(screen, ordered_horses)

        # All bought hay sheaves that stay in the van
        for item in van_hay:
            if not hay_in_van(item):
                continue
            bx = van_fill_rect.left + int(item["rel_x"] * van_fill_rect.width)
            by = van_fill_rect.top + int(item["rel_y"] * van_fill_rect.height)
            if dragged_van_hay is item:
                shop_art.draw_hay_shadow(screen, bx, by, hay_sw, hay_sh)
            screen.blit(hay_sprite, hay_sprite.get_rect(center=(bx, by)))

        if dragged_sheaf is not None:
            shop_art.draw_drop_prompt(screen, room, is_over_van)

        # Returning animated sheaf
        if anim_sheaf is not None:
            screen.blit(
                hay_sprite,
                hay_sprite.get_rect(center=(int(anim_pos[0]), int(anim_pos[1]))),
            )

        # Currently dragged counter sheaf
        if dragged_sheaf is not None:
            shop_art.draw_hay_shadow(screen, int(counter_drag_pos[0]), int(counter_drag_pos[1]),
                                     hay_sw, hay_sh)
            screen.blit(
                hay_sprite,
                hay_sprite.get_rect(
                    center=(int(counter_drag_pos[0]), int(counter_drag_pos[1]))
                ),
            )

        # Purchase popup
        if pygame.time.get_ticks() < message_until:
            msg_font = get_font(C.s(28), bold=True)
            msg_surf = msg_font.render(message, True, GOLD)
            msg_rect = msg_surf.get_rect(center=(room.w // 2, room.h - int(room.h * 0.16)))
            pygame.draw.rect(
                screen, (40, 20, 10), msg_rect.inflate(30, 16), border_radius=8
            )
            pygame.draw.rect(screen, GOLD, msg_rect.inflate(30, 16), 2, border_radius=8)
            screen.blit(msg_surf, msg_rect)

        hud.draw_time_lighting(screen)
        hud.draw_hud(screen, get_font(C.s(28), bold=True))
        pygame.display.flip()