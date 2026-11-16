"""farm.py — The farm scene.

Shows the yard: sky, fenced pen with a little house, the shed and the van
trailer. The horses you have caught stand in the van (physics horses built
from their own traits). Drag them out of the van into the fenced pen, where
they can't get out - or drag them back into the van. Put two horses in the
shed and close its doors to breed a random half-size foal.

Press ESC to go back to the world, or Give Up and choose Revive to restart.
Closing the window also quits the game.
"""

from collections.abc import Callable

import pygame

from game import constants as C
from game import daytime
from game import state
from game.display import get_screen
from game.gfx.horse_draw import draw_horses
from game.items import get_pixel_hay_sprite, hay_sprite_scale, sync_hay
from game.scenes.farm_art import (
    BASE_H,
    BASE_W,
    BREEDING_TIME,
    EAT_TIME,
    GIVE_UP_BUTTON_ZONE,
    PEN_AREA,
    PEN_ZONE,
    SHED_AREA,
    SHED_HANDLE_ZONE,
    SHED_ZONE,
    SLEEP_BUTTON_ZONE,
    VAN_AREA,
    VAN_ZONE,
    build_farm_scene,
    build_fence_overlay,
    build_shed_doors,
)
from game.sim import horse_care, ragdoll
from game.ui import hud
from game.ui.iris import Iris
from game.world_entities import WorldHorse


def run_farm(
    van_inventory: list,
    pen_horses: list,
    hay_items: list | None = None,
    on_day_passed: Callable[[], None] | None = None,
) -> bool:
    """Show the farm; return True when the player chooses to revive."""
    screen = get_screen()
    # Use the one hay store shared with the shop (merges in anything passed in)
    passed_hay = hay_items
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
    give_up_button_zone = to_screen(GIVE_UP_BUTTON_ZONE)

    # HAY POSITION HELPERS
    def hay_scale() -> int:
        return hay_sprite_scale(C.WIDTH)

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
        hay_w, hay_h = get_pixel_hay_sprite(hay_scale()).get_size()

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
            horse_care.kill_ragdoll(rag)

        rags.append(rag)
        return rag

    def grow_ragdoll(rag) -> None:
        area = {
            "van": van_area,
            "pen": pen_area,
            "shed": shed_area,
        }[rag.zone]
        ragdoll.resize_ragdoll(space, rag, area)

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

    for h in van_inventory:
        add_ragdoll(h, "van", van_area)

    for h in pen_horses:
        zone = getattr(h, "farm_zone", "pen")
        area = shed_area if zone == "shed" else pen_area
        add_ragdoll(h, zone, area)

    drag = {"rag": None, "ox": 0.0, "oy": 0.0, "hay": None, "hay_ox": 0, "hay_oy": 0}
    selected = None
    eating_hay: list[dict] = []   # {"rag": rag, "t": seconds eaten}
    iris = Iris()                 # closes and opens while sleeping
    restart_stats: dict[str, int] | None = None
    revive_button_rect = pygame.Rect(0, 0, 0, 0)
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
        return horse_care.can_breed([parent.world_horse for parent in parents])

    def handle_sleep() -> None:
        nonlocal status_message, status_timer, selected

        days_passed = daytime.advance(2)
        for _ in range(days_passed):
            for rag in list(rags):
                horse = rag.world_horse
                if horse.traits.get("dead", False):
                    continue

                death_reason, grew_up = horse_care.advance_horse_day(horse)
                if death_reason is not None:
                    horse_care.kill_ragdoll(rag)
                elif grew_up:
                    grow_ragdoll(rag)
            if on_day_passed is not None:
                on_day_passed()

        if selected in rags and selected.world_horse.traits.get("dead", False):
            selected = None

        status_message = "You slept."
        if days_passed:
            status_message += " A day passed; horses' stats were updated."
        status_timer = 3.0

    def request_sleep() -> None:
        """Sleep for two stages, with the iris wipe."""
        if iris.active:
            return
        iris.start((C.WIDTH // 2, C.HEIGHT // 2), handle_sleep)

    def capture_restart_stats() -> None:
        nonlocal restart_stats
        restart_stats = {
            "money": state.player_money,
            "horses_caught": state.horses_caught,
            "horses_killed": state.horses_killed,
            "bets_won": state.bets_won,
            "bets_lost": state.bets_lost,
            "days_survived": daytime.day_index + 1,
        }

    def draw_restart_summary(stats: dict[str, int]) -> None:
        title_font = pygame.font.SysFont("Arial", max(24, int(34 * C.U)), bold=True)
        line_font = pygame.font.SysFont("Arial", max(18, int(22 * C.U)))
        button_font = pygame.font.SysFont("Arial", max(16, int(20 * C.U)), bold=True)
        lines = (
            f"Money: ${stats['money']}",
            f"Horses caught: {stats['horses_caught']}",
            f"Horses killed: {stats['horses_killed']}",
            f"Bets won: {stats['bets_won']}",
            f"Bets lost: {stats['bets_lost']}",
            f"Days survived: {stats['days_survived']}",
        )
        title = title_font.render("Playthrough Stats", True, C.GOLD)
        line_surfaces = [line_font.render(line, True, C.WHITE) for line in lines]
        button_label = button_font.render("Revive", True, C.WHITE)
        button = pygame.Rect(
            0,
            0,
            max(C.s(160), button_label.get_width() + C.s(40)),
            max(C.s(44), button_label.get_height() + C.s(16)),
        )
        spacing = line_font.get_linesize() + C.s(8)
        button_gap = C.s(18)
        total_height = (
            title.get_height()
            + C.s(24)
            + len(line_surfaces) * spacing
            + button_gap
            + button.height
        )
        y = (C.HEIGHT - total_height) // 2
        screen.blit(
            title,
            title.get_rect(center=(C.WIDTH // 2, y + title.get_height() // 2)),
        )
        y += title.get_height() + C.s(24)
        for line in line_surfaces:
            screen.blit(
                line,
                line.get_rect(center=(C.WIDTH // 2, y + line.get_height() // 2)),
            )
            y += spacing
        button.topleft = (C.WIDTH // 2 - button.width // 2, y + button_gap)
        revive_button_rect.size = button.size
        revive_button_rect.topleft = button.topleft
        pygame.draw.rect(screen, (65, 130, 75), button, border_radius=8)
        pygame.draw.rect(screen, C.WHITE, button, 2, border_radius=8)
        screen.blit(button_label, button_label.get_rect(center=button.center))

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

        traits, sprite_right, sprite_left = horse_care.new_foal(
            parents[0].world_horse.traits,
            parents[1].world_horse.traits,
        )

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

    def try_feed_horse(item: dict, hx: int, hy: int) -> bool:
        """Feed hay dropped on a horse's mouth. True if it is being eaten."""
        nonlocal status_message, status_timer

        hay_w, hay_h = get_pixel_hay_sprite(hay_scale()).get_size()
        hay_rect = pygame.Rect(0, 0, hay_w, hay_h)
        hay_rect.center = (hx, hy)

        target = next(
            (rag for rag in reversed(rags)
             if horse_care.mouth_rect_of(rag).inflate(8, 8).colliderect(hay_rect)),
            None,
        )
        if target is None:
            if any(rag.race.rect().colliderect(hay_rect) for rag in rags):
                status_message = "Drop the hay at the horse's mouth to feed it."
                status_timer = 3.0
            return False

        traits = target.world_horse.traits
        name = getattr(target.race, "name", "") or traits.get("name", "") or "The horse"

        if traits.get("dead", False):
            status_message = f"{name} is dead and can't eat."
            status_timer = 3.0
            return False

        stats = ragdoll.ensure_stats(traits)
        if traits.get("hunger", "Full") in ("Full", "Fed"):
            status_message = f"{name} isn't hungry."
            status_timer = 3.0
            return False

        traits["hunger"] = "Full"
        if isinstance(stats, dict):
            stats["hunger"] = "Full"

        # The bale is used up: remove it everywhere it is stored
        for lst in (hay_items, passed_hay):
            if lst is not None:
                lst[:] = [x for x in lst if x is not item]

        # Start the eating animation at the horse's mouth
        eating_hay.append({"rag": target, "t": 0.0})
        status_message = f"{name} is eating the hay!"
        status_timer = 3.0
        return True

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
            if iris.active and event.type != pygame.QUIT:
                revive_clicked = (
                    restart_stats is not None
                    and event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and revive_button_rect.collidepoint(event.pos)
                )
                if not revive_clicked:
                    continue   # no input while the iris is closing or opening

            if event.type == pygame.QUIT:
                if drag["rag"] is not None:
                    drop(drag["rag"], mouse_pos)
                if breeding_remaining > 0:
                    complete_breeding()
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                return False

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if breeding_remaining > 0:
                    complete_breeding()
                if drag["rag"] is not None:
                    drop(drag["rag"], mouse_pos)
                return False

            if restart_stats is not None:
                if (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and revive_button_rect.collidepoint(event.pos)
                ):
                    return True
                continue

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                toggle_shed_doors()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if give_up_button_zone.collidepoint(event.pos):
                    if not iris.active:
                        iris.start(
                            (C.WIDTH // 2, C.HEIGHT // 2),
                            capture_restart_stats,
                        )
                    continue

                if sleep_button_zone.collidepoint(event.pos):
                    request_sleep()
                    continue

                if drag["rag"] is None and drag["hay"] is None:
                    # Check hay first so it can be picked up even near a horse.
                    hay_sprite = get_pixel_hay_sprite(hay_scale())
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
                    hay_sprite = get_pixel_hay_sprite(hay_scale())
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

                    if not try_feed_horse(drag["hay"], hx, hy):
                        save_hay_position(drag["hay"], hx, hy, settle=True)
                    drag["hay"] = None

                elif drag["rag"] is not None:
                    drop(drag["rag"], event.pos)
                    drag["rag"] = None
                    acc = 0.0

        if restart_stats is not None:
            iris.draw(screen)
            draw_restart_summary(restart_stats)
            pygame.display.flip()
            continue

        # Move the selected hay item anywhere in the farm.
        if drag["hay"] is not None:
            hay_sprite = get_pixel_hay_sprite(hay_scale())
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

        iris.update(dt)

        for entry in eating_hay[:]:
            entry["t"] += dt
            if entry["t"] >= EAT_TIME:
                eating_hay.remove(entry)

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
        hay_sprite = get_pixel_hay_sprite(hay_scale())
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

        # Hay being eaten: spins and shrinks at the horse's mouth
        eat_sprite = get_pixel_hay_sprite(hay_scale())
        for entry in eating_hay:
            progress = min(1.0, entry["t"] / EAT_TIME)
            mouth = horse_care.mouth_rect_of(entry["rag"])
            small = pygame.transform.scale(
                eat_sprite,
                (
                    max(1, int(eat_sprite.get_width() * (1.0 - progress))),
                    max(1, int(eat_sprite.get_height() * (1.0 - progress))),
                ),
            )
            spun = pygame.transform.rotate(small, progress * 720)
            screen.blit(spun, spun.get_rect(center=mouth.center))

        screen.blit(fence, (0, 0))

        if not shed_doors_open:
            screen.blit(closed_shed_doors, (0, 0))

        hud.draw_time_lighting(screen)
        give_up_btn_rect = to_screen(GIVE_UP_BUTTON_ZONE)
        pygame.draw.rect(screen, C.DARK_RED, give_up_btn_rect, border_radius=6)
        pygame.draw.rect(screen, C.WHITE, give_up_btn_rect, 2, border_radius=6)
        give_up_label = sleep_button_font.render("Suicide", True, C.WHITE)
        screen.blit(give_up_label, give_up_label.get_rect(center=give_up_btn_rect.center))

        sleep_btn_rect = to_screen(SLEEP_BUTTON_ZONE)
        pygame.draw.rect(
            screen,
            (70, 130, 180),
            sleep_btn_rect,
            border_radius=6,
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

        iris.draw(screen)
        if restart_stats is not None:
            draw_restart_summary(restart_stats)

        pygame.display.flip()