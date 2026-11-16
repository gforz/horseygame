"""glue.py — The scale house ("Glue") and its horse-weighing treadmill.

Walk a caught horse up the treadmill and it is sold by weight: $5 per 100 lb.
Horses in the van are simulated as ragdolls you can drag around.
"""

import math

import pygame

from game import constants as C
from game import state
from game.gfx.fonts import get_font
from game.gfx.horse_draw import draw_horses
from game.items import get_pixel_hay_sprite, hay_in_van, sync_hay
from game.scenes import glue_art
from game.sim import ragdoll
from game.sim.horse_care import kill_ragdoll
from game.ui import hud
from game.world_entities import Van


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


def _horse_on_treadmill(
    rag: ragdoll.Ragdoll, treadmill: pygame.Rect, tolerance: int
) -> bool:
    bounds = rag.race.rect()
    return (
        bounds.right > treadmill.left
        and bounds.left < treadmill.right
        and abs(bounds.bottom - glue_art.belt_y(treadmill)) <= tolerance
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


def run_scale_house(horses: list, on_sold=None, van=None) -> None:
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

    layout = glue_art.treadmill_layout(treadmill_rect)
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
    # Collision boundary at bottom of screen so horses cannot fall out
    space.add_edge((-1000, screen.get_height() - 4), (screen.get_width() + 1000, screen.get_height() - 4), friction=2.5)
    treadmill_floor_y = glue_art.belt_y(treadmill_rect)
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

        # A dead horse goes completely floppy in the scale house too
        if horse.traits.get("dead", False):
            kill_ragdoll(van_rag)

        rags.append(van_rag)

    # One hay store shared with the shop and the farm
    van_hay = sync_hay(
        van.hay_items
        if (van and hasattr(van, "hay_items"))
        else (Van.last_instance.hay_items if Van.last_instance else [])
    )
    k_hay = max(2, int(van_scale_x * 1.6))
    hay_sprite = get_pixel_hay_sprite(k_hay)
    hay_sw, hay_sh = hay_sprite.get_size()

    drag: dict = {"rag": None, "ox": 0.0, "oy": 0.0, "hay": None, "hay_ox": 0.0, "hay_oy": 0.0}
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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and drag["rag"] is None and drag["hay"] is None:
                # Check if clicked on a hay sheaf in the van
                clicked_hay = None
                for item in reversed(van_hay):
                    if not hay_in_van(item):
                        continue
                    hx = van_area.left + int(item["rel_x"] * van_area.width)
                    hy = van_area.top + int(item["rel_y"] * van_area.height)
                    if math.hypot(event.pos[0] - hx, event.pos[1] - hy) <= max(hay_sw, hay_sh) * 0.9:
                        clicked_hay = item
                        drag["hay"] = item
                        drag["hay_ox"] = hx - event.pos[0]
                        drag["hay_oy"] = hy - event.pos[1]
                        break

                if clicked_hay is None:
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
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if drag["hay"] is not None:
                    drag["hay"] = None
                if drag["rag"] is not None:
                    hit = drag["rag"]
                    ragdoll.freeze(hit.race)
                    ragdoll.set_drag_collisions(hit, enabled=True)
                    drag["rag"] = None
                    physics_accumulator = 0.0

        if drag["hay"] is not None:
            tx = mouse_pos[0] + drag["hay_ox"]
            ty = mouse_pos[1] + drag["hay_oy"]
            margin_x = hay_sw // 2
            margin_y = hay_sh // 2
            tx = max(van_area.left + margin_x, min(van_area.right - margin_x, tx))
            ty = max(van_area.top + margin_y, min(van_area.bottom - margin_y, ty))
            drag["hay"]["rel_x"] = (tx - van_area.left) / float(max(1, van_area.width))
            drag["hay"]["rel_y"] = (ty - van_area.top) / float(max(1, van_area.height))

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
                state.player_money += payout
            sale_popup = f"+${payout}"
            sale_popup_until = pygame.time.get_ticks() + 2500

        on_scale = [
            rag for rag in rags
            if rag is not drag["rag"] and _horse_on_scale(
                rag, scale_platform, max(12, round(6 * scale_factor))
            )
        ]
        total_weight = sum(_horse_weight(rag) for rag in on_scale)

        screen.fill(glue_art.BACKGROUND)

        # 1. Background elements behind treadmill & horses
        glue_art.draw_house_behind_treadmill(screen, treadmill_rect)

        # 2. Treadmill belt
        glue_art.draw_treadmill(screen, treadmill_rect, belt_phase)
        glue_art.draw_treadmill_label(screen, layout, treadmill_rect)

        # 3. The brass scale, top left
        glue_art.draw_scale(
            screen, scale_art, scale_factor, scale_top,
            bool(on_scale), total_weight,
        )

        glue_art.draw_van(screen, van_rect)

        # 4. Draw horses in the middle layer
        ordered = [rag.race for rag in rags if rag is not drag["rag"]]
        if drag["rag"] is not None:
            ordered.append(drag["rag"].race)
        draw_horses(screen, ordered)

        # Draw the hay stored in the van (hay left on the farm is skipped).
        for item in van_hay:
            if not hay_in_van(item):
                continue
            hx = van_area.left + int(item.get("rel_x", 0.5) * van_area.width)
            hy = van_area.top + int(item.get("rel_y", 0.5) * van_area.height)
            if drag["hay"] is item:
                shadow_w, shadow_h = max(1, int(hay_sw * 1.1)), max(1, int(hay_sh * 0.3))
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), (0, 0, shadow_w, shadow_h))
                screen.blit(shadow_surf, (hx - shadow_w // 2, hy + hay_sh // 2 + 4))
            screen.blit(hay_sprite, hay_sprite.get_rect(center=(hx, hy)))

        # 5. The pink wall, right pillar and corner, in front of the horses
        glue_art.draw_house_front(screen, treadmill_rect)

        hud.draw_time_lighting(screen)
        hud.draw_hud(screen, get_font(C.s(28), bold=True))
        if pygame.time.get_ticks() < sale_popup_until:
            popup_font = get_font(max(24, C.s(40)), bold=True)
            popup = popup_font.render(f"Sold horse! {sale_popup}", True, (255, 238, 120))
            popup_rect = popup.get_rect(center=(screen.get_width() // 2, C.s(70)))
            popup_bg = popup_rect.inflate(C.s(36), C.s(22))
            pygame.draw.rect(screen, (55, 35, 29), popup_bg, border_radius=C.s(10))
            pygame.draw.rect(screen, C.GOLD, popup_bg, max(2, C.s(3)), border_radius=C.s(10))
            screen.blit(popup, popup_rect)
        pygame.display.flip()