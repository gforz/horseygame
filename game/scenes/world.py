"""world.py — Overworld map game loop.

Responsible for:
  - Spawning and managing wandering WorldHorse objects
  - Player movement (Player class)
  - Lasso mechanic (Lasso class)
  - Van inventory UI (Van class)
  - Camera management
  - Triggering the race track, the farm, the scale house and the shop

All constants, drawing helpers and classes are imported from their
dedicated modules.
"""

import math
import random

import pygame

from game import constants as C
from game import daytime
from game import state
from game.display import get_screen
from game.gfx.fonts import get_font
from game.gfx.horse_draw import draw_horses
from game.gfx.horse_model import roll_world_horse_traits
from game.gfx.track_art import build_race_track_sprite, draw_race_track
from game.gfx.world_art import (
    build_ground,
    draw_ground,
    draw_world_characters,
    screen_to_world,
    update_camera,
)
from game.gfx.world_horse_sprite import build_horse_sprite
from game.items import get_pixel_hay_sprite, hay_in_van
from game.items import get_pixel_hay_sprite, hay_in_van
from game.scenes.farm import run_farm
from game.scenes.glue import run_scale_house
from game.scenes.race import run_track
from game.scenes.shop import run_shop
from game.sim import horse_care, ragdoll
from game.sim.horse_care import kill_ragdoll
from game.sim.race_horse import RaceHorse
from game.ui import hud
from game.ui.iris import Iris
from game.world_entities import Lasso, Player, Van, WorldHorse
from game.world_map import (
    FARM_POS,
    HOUSE_POSITION,
    SHOP_POS,
    build_farm_sprite,
    build_house_sprite,
    build_shop_sprite,
    draw_van_interior,
    near_farm,
    near_house,
    near_shop,
    van_geometry,
)


def _restore_horse_to_world(
    horse: WorldHorse,
    horses: list[WorldHorse],
    horse_start_state: dict[int, str],
) -> None:
    if horse not in horses:
        horses.append(horse)
    horse_start_state.setdefault(id(horse), "idle")
    horse.state = horse_start_state[id(horse)]


def _make_world_horses(player: Player, obstacles: list) -> tuple[list, dict]:
    """Spawn HORSE_COUNT horses at valid, unoccupied positions."""
    horses: list[WorldHorse] = []
    horse_start_state: dict[int, str] = {}   # id(horse) -> state it spawned with

    for _ in range(C.HORSE_COUNT):
        traits       = roll_world_horse_traits()
        ragdoll.ensure_stats(traits)
        sprite_right = build_horse_sprite(traits)
        sprite_left  = pygame.transform.flip(sprite_right, True, False)

        h = WorldHorse(traits, sprite_right, sprite_left,
                       x=float(C.WORLD_WIDTH // 2),
                       y=float(C.WORLD_HEIGHT - 80))

        # Find a valid spawn position
        for _ in range(200):
            test_x = random.randint(80, C.WORLD_WIDTH  - 80)
            test_y = random.randint(150, C.WORLD_HEIGHT - 20)
            if not h.can_stand(test_x, test_y, obstacles):
                continue
            if (test_x - player.x) ** 2 + (test_y - player.y) ** 2 < 400 ** 2:
                continue
            h.x = float(test_x)
            h.y = float(test_y)
            break

        horse_start_state[id(h)] = h.state
        horses.append(h)

    return horses, horse_start_state


def _simulate_wild_horse_day(
    horses: list[WorldHorse],
    player: Player,
    obstacles: list,
    horse_start_state: dict[int, str],
) -> None:
    """Breed wild horses, then cull only horses present at the day's start."""
    for horse in tuple(horses):
        if horse.state != "caught" and not horse.traits.get("dead", False):
            horse_care.advance_wild_foal_day(horse)

    breeders = [
        horse for horse in horses
        if horse.state != "caught" and not horse.traits.get("dead", False)
    ]

    if len(breeders) >= 2:
        for _ in range(random.randint(55, 65)):
            parent_a, parent_b = random.sample(breeders, 2)
            traits, sprite_right, sprite_left = horse_care.new_foal(
                parent_a.traits, parent_b.traits
            )
            foal = WorldHorse(
                traits, sprite_right, sprite_left, x=0.0, y=0.0
            )

            for _ in range(200):
                x = random.randint(80, C.WORLD_WIDTH - 80)
                y = random.randint(150, C.WORLD_HEIGHT - 20)
                if not foal.can_stand(x, y, obstacles):
                    continue
                if (x - player.x) ** 2 + (y - player.y) ** 2 < 400 ** 2:
                    continue
                foal.x, foal.y = float(x), float(y)
                break
            else:
                raise RuntimeError("Unable to find a valid world spawn for a foal.")

            horses.append(foal)
            horse_start_state[id(foal)] = foal.state

    death_count = min(random.randint(50, 60), len(breeders))
    for horse in random.sample(breeders, death_count):
        horse.traits["dead"] = True
        horses.remove(horse)
        horse_start_state.pop(id(horse), None)


def run_world(open_with_iris: bool = False) -> bool:
    """Run the overworld; return True when the farm requests a restart."""

    # --- Screen setup ---
    screen = get_screen()
    pygame.display.set_caption("Horse Racing World")
    clock  = pygame.time.Clock()
    opening_iris = Iris() if open_with_iris else None
    if opening_iris is not None:
        opening_iris.start_open((C.WIDTH // 2, C.HEIGHT // 2))

    # --- Static world decorations (seeded for reproducibility) ---
    random.seed(12)

    # Keep the existing flower placements stable after removing the scattered
    # grass squares that used to consume this part of the seeded sequence.
    decor_random = random.Random(12)
    for _ in range(7000):
        decor_random.randint(0, C.WORLD_WIDTH)
        decor_random.randint(0, C.WORLD_HEIGHT)
        decor_random.choice([C.DARK_GRASS, C.LIGHT_GRASS, C.GRASS])

    flowers = [
        (
            decor_random.randint(0, C.WORLD_WIDTH),
            decor_random.randint(0, C.WORLD_HEIGHT),
            decor_random.choice([(255,225,130), (245,170,180), (230,230,245)]),
        )
        for _ in range(100)
    ]

    random.seed()   # back to random seed for gameplay

    # --- Build static sprites (once) ---
    ground       = build_ground(flowers)
    track_sprite = build_race_track_sprite()
    track_rect   = pygame.Rect(0, 0, 620, 460)
    track_rect.center = (C.WORLD_WIDTH // 2, C.WORLD_HEIGHT // 2)

    farm_sprite  = build_farm_sprite()
    farm_rect    = farm_sprite.get_rect(topleft=FARM_POS)
    house_sprite = build_house_sprite()
    house_rect   = house_sprite.get_rect(topleft=HOUSE_POSITION)

    shop_sprite  = build_shop_sprite()
    shop_rect    = shop_sprite.get_rect(topleft=SHOP_POS)

    # Horses can't wander onto the track, farm, house, or shop
    horse_obstacles = [
        track_rect.inflate(80, 80),
        farm_rect.inflate(80, 80),
        house_rect.inflate(40, 40),
        shop_rect.inflate(40, 40),
    ]

    # --- Game objects ---
    player = Player(
        x=float(farm_rect.centerx),
        y=float(farm_rect.bottom + 70),
    )
    lasso  = Lasso()
    van    = Van()
    pen_horses: list[WorldHorse] = []   # horses living in the farm pen

    horses, horse_start_state = _make_world_horses(player, horse_obstacles)

    def process_world_day() -> None:
        _simulate_wild_horse_day(
            horses, player, horse_obstacles, horse_start_state
        )

    debug_day_chord_held = False

    # --- Camera ---
    camera_x, camera_y = update_camera(player.x, player.y)

    # --- Fonts ---
    font         = get_font(24, bold=True)
    money_font   = get_font(C.s(28), bold=True)

    # Dark overlay shown behind the van interior
    van_dim = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    van_dim.fill((0, 0, 0, 120))

    # Van physics: caught horses are simulated like the race horses
    van_trailer, van_inside, k = van_geometry()
    van_space   = ragdoll.create_space()
    ragdoll.add_box_walls(van_space, van_inside)
    van_space.add_edge((-1000, C.HEIGHT - 4), (C.WIDTH + 1000, C.HEIGHT - 4), friction=2.5)
    van_horses: dict[int, ragdoll.Ragdoll] = {}   # id(world horse) -> VanRagdoll
    van_acc     = 0.0
    drag        = {"vh": None, "ox": 0.0, "oy": 0.0, "last": None, "hay": None, "hay_ox": 0.0, "hay_oy": 0.0}
    sel         = {"vh": None}   # horse whose stats panel is showing (right-click)

    def freeze(rag: RaceHorse) -> None:
        """Zero all motion on a horse (used when grabbing / dropping it)."""
        ragdoll.freeze(rag)

    def cancel_drag() -> None:
        sel["vh"] = None
        if drag["vh"] is not None:
            freeze(drag["vh"].race)
        drag["vh"], drag["last"] = None, None
        drag["hay"] = None

    def release_to_world(vh: ragdoll.Ragdoll) -> None:
        """Take a horse out of the van and drop it back into the world."""
        h = vh.world_horse
        try:
            van.inventory.remove(h)
        except (ValueError, AttributeError):
            pass
        h.x = float(player.x + random.uniform(-70, 70))
        h.y = float(player.y + random.uniform(60, 120))
        _restore_horse_to_world(h, horses, horse_start_state)

    def enter_building(action):
        """Run a building's scene, then restore the overworld display."""
        nonlocal screen, clock, debug_day_chord_held
        result = action()
        screen = get_screen()
        pygame.display.set_caption("Horse Racing World")
        clock  = pygame.time.Clock()
        keys = pygame.key.get_pressed()
        debug_day_chord_held = all(
            keys[key] for key in (pygame.K_d, pygame.K_a, pygame.K_y)
        )
        return result

    def sell_caught_horse(horse: WorldHorse, payout: int) -> None:
        for collection in (van.inventory, horses):
            if horse in collection:
                collection.remove(horse)
        horse_start_state.pop(id(horse), None)
        state.player_money += payout

    hint_text = ""      # short hint shown at the top of the screen
    hint_until = 0

    running = True

    while running:
        frame_dt = clock.tick(C.FPS_OVERWORLD) / 1000.0
        dt = min(frame_dt, 0.05)
        if opening_iris is not None:
            opening_iris.update(dt)
        mouse_pos = pygame.mouse.get_pos()

        # --------------------------------------------------------
        # EVENTS
        # --------------------------------------------------------
        for event in pygame.event.get():

            if opening_iris is not None and opening_iris.active and event.type != pygame.QUIT:
                continue

            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if van.open:
                        cancel_drag()
                        van.toggle()
                    else:
                        running = False

                if event.key == pygame.K_v:
                    cancel_drag()
                    van.toggle()
                    van_acc = 0.0

                if event.key == pygame.K_e and not van.open:
                    if player.near_track(track_rect) and daytime.is_night():
                        hint_text = "The track is empty at night. Sleep at the farm."
                        hint_until = pygame.time.get_ticks() + 2500

                    elif player.near_track(track_rect):
                        enter_building(
                            lambda: run_track(
                                [*van.inventory, *pen_horses],
                                on_day_passed=process_world_day,
                            )
                        )

                    elif near_farm(player, farm_rect):
                        restart_requested = enter_building(
                            lambda: run_farm(van.inventory, pen_horses,
                                             hay_items=van.hay_items,
                                             on_day_passed=process_world_day)
                        )
                        if restart_requested:
                            return True

                    elif near_house(player, house_rect) and daytime.is_night():
                        hint_text = "Glue is closed at night."
                        hint_until = pygame.time.get_ticks() + 2500

                    elif near_house(player, house_rect):
                        caught_horses = list(dict.fromkeys(van.inventory))
                        enter_building(
                            lambda: run_scale_house(caught_horses,
                                                    on_sold=sell_caught_horse,
                                                    van=van)
                        )

                    elif near_shop(player, shop_rect) and daytime.is_night():
                        hint_text = "The shop is closed at night."
                        hint_until = pygame.time.get_ticks() + 2500

                    elif near_shop(player, shop_rect):
                        enter_building(lambda: run_shop(van=van))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if van.open:
                    # Check if a hay sheaf in the van was clicked
                    _, van_inside_geom, k_geom = van_geometry()
                    k_hay = max(2, int(k_geom * 1.4))
                    hay_sprite = get_pixel_hay_sprite(k_hay)
                    hay_sw, hay_sh = hay_sprite.get_size()

                    clicked_hay = None
                    for item in reversed(van.hay_items):
                        if not hay_in_van(item):
                            continue
                        hx = van_inside_geom.left + int(item["rel_x"] * van_inside_geom.width)
                        hy = van_inside_geom.top + int(item["rel_y"] * van_inside_geom.height)
                        if math.hypot(event.pos[0] - hx, event.pos[1] - hy) <= max(hay_sw, hay_sh) * 0.9:
                            clicked_hay = item
                            drag["hay"] = item
                            drag["hay_ox"] = hx - event.pos[0]
                            drag["hay_oy"] = hy - event.pos[1]
                            break

                    if clicked_hay is None and drag["vh"] is None:
                        # Grab a horse in the van
                        for vh in reversed(list(van_horses.values())):
                            if vh.race.rect().collidepoint(event.pos):
                                torso = vh.race.torso
                                drag["vh"]   = vh
                                drag["ox"]   = torso.position.x - event.pos[0]
                                drag["oy"]   = torso.position.y - event.pos[1]
                                drag["last"] = (torso.position.x, torso.position.y)
                                freeze(vh.race)
                                van_acc = 0.0
                                break
                else:
                    # Throw lasso
                    world_mx, world_my = screen_to_world(
                        mouse_pos[0], mouse_pos[1], camera_x, camera_y
                    )
                    angle     = math.atan2(world_my - player.y, world_mx - player.x)
                    cos_a     = math.cos(angle)
                    sin_a     = math.sin(angle)
                    target_x  = player.x + cos_a * C.LASSO_MAX_RANGE
                    target_y  = player.y + sin_a * C.LASSO_MAX_RANGE
                    if lasso.active:
                        pass
                    elif state.lasso_count > 0:
                        lasso.throw(player.x, player.y, target_x, target_y)
                    else:
                        hint_text = "No lassos! Buy one at the shop."
                        hint_until = pygame.time.get_ticks() + 2000

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and van.open:
                # Right-click a horse in the van to show its stats
                hit = None
                for vh in reversed(list(van_horses.values())):
                    if vh.race.rect().collidepoint(event.pos):
                        hit = vh
                        break
                sel["vh"] = None if hit is sel["vh"] else hit

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if drag["hay"] is not None:
                    drag["hay"] = None
                if drag["vh"] is not None:
                    vh = drag["vh"]
                    freeze(vh.race)
                    drag["vh"], drag["last"] = None, None
                    van_acc = 0.0
                    if not van_trailer.collidepoint(event.pos):
                        release_to_world(vh)      # dropped outside the van -> back to the world

        # --------------------------------------------------------
        # UPDATE
        # --------------------------------------------------------
        keys = pygame.key.get_pressed()
        debug_chord_pressed = all(
            keys[key] for key in (pygame.K_d, pygame.K_a, pygame.K_y)
        )
        if (
            debug_chord_pressed
            and not debug_day_chord_held
            and not van.open
            and (opening_iris is None or not opening_iris.active)
        ):
            for _ in range(daytime.advance(len(daytime.STAGES))):
                for horse in [*van.inventory, *pen_horses]:
                    if not horse.traits.get("dead", False):
                        horse_care.advance_horse_day(horse)
                process_world_day()
            hint_text = "Debug: advanced one full day"
            hint_until = pygame.time.get_ticks() + 2500
        debug_day_chord_held = debug_chord_pressed

        if not van.open:
            player.update(keys, frame_dt)

        lasso.update(horses, player.x, player.y)

        # Add freshly caught horses to van
        for h in horses:
            if h.state == "caught" and h not in van.inventory and h not in pen_horses:
                van.add(h)
                state.horses_caught += 1
                state.lasso_count = max(0, state.lasso_count - 1)   # one lasso used per horse

        for h in horses:
            if not h.traits.get("dead", False):
                h.update(horse_obstacles, dt)

        camera_x, camera_y = update_camera(player.x, player.y)

        # --------------------------------------------------------
        # DRAW
        # --------------------------------------------------------
        draw_ground(screen, ground, camera_x, camera_y)
        draw_race_track(screen, track_sprite, track_rect, camera_x, camera_y)

        # Farm, House, and Shop buildings (transparent background, grass shows through)
        screen.blit(farm_sprite, (farm_rect.x - camera_x, farm_rect.y - camera_y))
        screen.blit(house_sprite, (house_rect.x - camera_x, house_rect.y - camera_y))
        screen.blit(shop_sprite, (shop_rect.x - camera_x, shop_rect.y - camera_y))

        draw_world_characters(screen, player, horses, camera_x, camera_y)

        lasso.draw(screen, player.x, player.y, camera_x, camera_y)
        hud.draw_time_lighting(screen)
        if daytime.is_night() and not van.open:
            player.draw_headlights(screen, camera_x, camera_y)

        # Interaction prompt
        prompt_text = None
        if not van.open:
            if player.near_track(track_rect):
                prompt_text = ("The race track is empty at night" if daytime.is_night()
                               else "Press E to enter the race track")
            elif near_farm(player, farm_rect):
                prompt_text = "Press E to enter the farm"
            elif near_house(player, house_rect):
                prompt_text = ("Glue is closed at night" if daytime.is_night()
                               else "Press E to enter Glue")
            elif near_shop(player, shop_rect):
                prompt_text = ("The shop is closed at night" if daytime.is_night()
                               else "Press E to enter the shop")

        if prompt_text:
            prompt    = font.render(prompt_text, True, C.WORLD_WHITE)
            prompt_bg = pygame.Rect(C.WIDTH // 2 - 270, C.HEIGHT - 85, 540, 48)
            pygame.draw.rect(screen, C.DARK_BROWN, prompt_bg, border_radius=8)
            screen.blit(prompt, prompt.get_rect(center=prompt_bg.center))

        # Van interior (farm-style trailer) + inventory overlay
        if van.open:
            draw_van_interior(screen, van_dim)

            # Keep the van's horses in sync with what has been caught / released
            in_van = {id(h): h for h in van.inventory}
            for hid in list(van_horses):
                if hid not in in_van:
                    if drag["vh"] is van_horses[hid]:
                        drag["vh"], drag["last"] = None, None
                    van_space.remove(*van_horses[hid].parts)
                    if sel["vh"] is van_horses[hid]:
                        sel["vh"] = None
                    del van_horses[hid]
            for hid, h in in_van.items():
                if hid not in van_horses:
                    race, parts = ragdoll.build_ragdoll(van_space, len(van_horses), van_inside, h.traits)
                    van_rag = ragdoll.Ragdoll(h, race, parts)
                    if h.traits.get("dead", False):
                        # Dead horses are floppy in the van too
                        kill_ragdoll(van_rag, wake=False)
                    van_horses[hid] = van_rag

            # Dragging: the horse follows the mouse (same method as track.py)
            if drag["vh"] is not None:
                rag      = drag["vh"].race
                target_x = mouse_pos[0] + drag["ox"]
                target_y = mouse_pos[1] + drag["oy"]
                old_x, old_y = drag["last"]
                dx, dy = target_x - old_x, target_y - old_y

                rag.torso.position = (target_x, target_y)
                rag.torso.velocity = (0, 0)
                rag.torso.angular_velocity = 0
                rag.head.body.position = (
                    rag.head.body.position.x + dx,
                    rag.head.body.position.y + dy,
                )
                rag.head.body.velocity = (0, 0)
                rag.head.body.angular_velocity = 0
                rag.head.stop()
                rag.tail.body.position = (
                    rag.tail.body.position.x + dx,
                    rag.tail.body.position.y + dy,
                )
                rag.tail.body.velocity = (0, 0)
                rag.tail.body.angular_velocity = 0
                rag.tail.stop()
                for leg in rag.legs:
                    leg.body.position = (leg.body.position.x + dx, leg.body.position.y + dy)
                    leg.body.velocity = (0, 0)
                    leg.body.angular_velocity = 0
                    leg.stop()
                drag["last"] = (target_x, target_y)

            # Horses move with the same gait logic as on the track (unless dead)
            for vh in van_horses.values():
                if not vh.world_horse.traits.get("dead", False):
                    vh.race.update(dt, is_dragged=(vh is drag["vh"]))

            van_acc += dt
            while van_acc >= C.PHYSICS_STEP:
                van_space.step(C.PHYSICS_STEP)
                van_acc -= C.PHYSICS_STEP

            # Dragged horse is drawn last so it sits on top
            ordered = [vh.race for vh in van_horses.values() if vh is not drag["vh"]]
            if drag["vh"] is not None:
                ordered.append(drag["vh"].race)
            draw_horses(screen, ordered)

            # Update and draw hay items in the van
            _, _, k = van_geometry()
            k_hay = max(2, int(k * 1.4))
            hay_sprite = get_pixel_hay_sprite(k_hay)
            hay_sw, hay_sh = hay_sprite.get_size()
            if drag["hay"] is not None:
                tx = mouse_pos[0] + drag["hay_ox"]
                ty = mouse_pos[1] + drag["hay_oy"]
                margin_x = hay_sw // 2
                margin_y = hay_sh // 2
                tx = max(van_inside.left + margin_x, min(van_inside.right - margin_x, tx))
                ty = max(van_inside.top + margin_y, min(van_inside.bottom - margin_y, ty))
                drag["hay"]["rel_x"] = (tx - van_inside.left) / float(max(1, van_inside.width))
                drag["hay"]["rel_y"] = (ty - van_inside.top) / float(max(1, van_inside.height))

            for item in van.hay_items:
                if not hay_in_van(item):
                    continue
                hx = van_inside.left + int(item["rel_x"] * van_inside.width)
                hy = van_inside.top + int(item["rel_y"] * van_inside.height)
                if drag["hay"] is item:
                    shadow_w, shadow_h = int(hay_sw * 1.1), int(hay_sh * 0.3)
                    shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), (0, 0, shadow_w, shadow_h))
                    screen.blit(shadow_surf, (hx - shadow_w // 2, hy + hay_sh // 2 + 4))
                screen.blit(hay_sprite, hay_sprite.get_rect(center=(hx, hy)))

            if sel["vh"] is not None and not sel["vh"].world_horse.traits.get("dead", False):
                ragdoll.draw_stats_panel(screen, sel["vh"].race, sel["vh"].world_horse.traits)

        # Draw Clean Money Display on Top Left
        hud.draw_hud(screen, money_font)

        if pygame.time.get_ticks() < hint_until:
            hint = font.render(hint_text, True, C.WORLD_WHITE)
            hint_bg = hint.get_rect(center=(C.WIDTH // 2, C.s(40))).inflate(30, 16)
            pygame.draw.rect(screen, C.DARK_BROWN, hint_bg, border_radius=8)
            screen.blit(hint, hint.get_rect(center=hint_bg.center))

        if opening_iris is not None:
            opening_iris.draw(screen)

        pygame.display.flip()

    return False