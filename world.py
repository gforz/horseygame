"""
world.py — Overworld map game loop.

Responsible for:
  - Spawning and managing wandering WorldHorse objects
  - Player movement (Player class)
  - Lasso mechanic (Lasso class)
  - Van inventory UI (Van class)
  - Camera management
  - Triggering the race track via run_track()
  - Triggering the farm via run_farm()
  - Triggering the scale house via run_scale_house()
  - Triggering the shop via run_shop()

All constants, drawing helpers and classes are imported from their
dedicated modules.
"""

import math
import random

import pygame

import constants as C
import ragdoll
from classes import WorldHorse, Lasso, Van, Player, RaceHorse
from methods import (
    get_font,
    build_race_track_sprite,
    build_horse_sprite,
    roll_world_horse_traits,
    draw_grass,
    draw_race_track,
    draw_world_characters,
    draw_horses,
    update_camera,
    screen_to_world,
)
import track
from track import run_track
from farm import run_farm, get_screen, VAN_BORDER, VAN_FILL, VAN_BED, WHEEL, HUB
from glue import (
    HOUSE_POSITION,
    build_house_sprite,
    near_house,
    run_scale_house,
)
from shop import run_shop


# ============================================================
# FARM BUILDING HELPERS
# ============================================================

FARM_SCALE         = 2           # sprite is drawn at 130x130 -> 260x260 in the world
FARM_POS           = (120, 130)  # top-left of the farm in world coordinates
FARM_INTERACT_DIST = 120         # how close the player must be to the gate


# ============================================================
# SHOP BUILDING HELPERS
# ============================================================

SHOP_SCALE         = 6           # scale factor to make it crisp and well-sized in the world
SHOP_POS           = (1500, 180) # top-left of the shop in world coordinates
SHOP_INTERACT_DIST = 120         # how close the player must be to enter the shop


def _restore_horse_to_world(
    horse: WorldHorse,
    horses: list[WorldHorse],
    horse_start_state: dict[int, str],
) -> None:
    if horse not in horses:
        horses.append(horse)
    horse_start_state.setdefault(id(horse), "idle")
    horse.state = horse_start_state[id(horse)]


def build_shop_sprite() -> pygame.Surface:
    """Draw the shop building on a transparent surface using pixel art from the reference image.

    No image file needed. The surface is fully transparent, so the grass
    background shows through everywhere.
    """
    pixels = (
        ".........................KK",
        ".........................KK",
        "........WWWWWWWWWWWWWWWWWWW",
        "........WYYYYWWWWCCWWCCWWWW",
        "........WYYYYWWWWCCWWCCWWWW",
        "........WWWWWWWWWWWWWWWWWWW",
        "......DDDDDDDDDDDDDDDDDDDDD",
        "......DDDDDDDDDDDDDDDDDDDDD",
        "......DMMMMMMMMMMMMMMMMMMMMBB",
        "......DMGGGGMMWWWWMMGGGGMMMBB",
        "......DMGGGGMMWWWWMMGGGGMMMBB",
        "......DMMMMMMMMMMMMMMMMMMMMMB",
        "......DMMMMMMBBBBMMMMMMMMMMMB",
        "......DMMMMMMBBBBMMMMMMMMMMMB",
        "......SSSSSSSSSSSSSSSSSSSSSSS",
        "......SSSSSSSSSSSSSSSSSSSSSSS",
        "....KKSSSSSSSSSSSSSSSSSSSKK..",
        "....KKSSSSSSSSSSSSSSSSSSSKK..",
    )
    palette = {
        ".": (0, 0, 0, 0),          # Transparent background
        "K": (24, 22, 23),          # Feet/shadow blocks
        "D": (150, 75, 30),         # Roof trim / top board frame
        "W": (255, 255, 255),       # White sign background
        "Y": (210, 210, 50),        # Yellow icons on sign
        "C": (100, 60, 30),         # Brown rope/lasso icons on sign
        "M": (130, 80, 35),         # Main wooden walls
        "G": (50, 200, 200),        # Cyan windows and double doors
        "B": (100, 60, 30),         # Right side wall depth shading
        "S": (110, 65, 30),         # Lower foundation / base shading
    }

    width = max(map(len, pixels))
    height = len(pixels)
    img = pygame.Surface((width, height), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, color in enumerate(row):
            if color != ".":
                img.set_at((x, y), palette[color])

    return pygame.transform.scale(
        img, (width * SHOP_SCALE, height * SHOP_SCALE)
    )


def near_shop(player, shop_rect: pygame.Rect) -> bool:
    """True when the player is close to the shop's entrance (bottom-centre)."""
    gate_x, gate_y = shop_rect.centerx, shop_rect.bottom
    return math.hypot(player.x - gate_x, player.y - gate_y) <= SHOP_INTERACT_DIST


def build_farm_sprite() -> pygame.Surface:
    """Draw the farm (fenced yard + house) on a transparent surface.

    No image file needed. The surface is transparent, so the grass
    background shows through everywhere that isn't fence or house.
    """
    size = 130
    img  = pygame.Surface((size, size), pygame.SRCALPHA)

    fence      = (190, 155, 40)
    fence_dark = (160, 125, 25)
    hole       = (0, 0, 0, 0)          # transparent "dashes" in the rails

    rail = 9
    gate_l, gate_r = 52, 78             # gap in the bottom fence

    # --- Fence rails ---
    pygame.draw.rect(img, fence, (0, 0, size, rail))                    # top
    pygame.draw.rect(img, fence, (0, 0, rail, size))                    # left
    pygame.draw.rect(img, fence, (size - rail, 0, rail, size))           # right
    pygame.draw.rect(img, fence, (0, size - rail, gate_l, rail))        # bottom-left
    pygame.draw.rect(img, fence, (gate_r, size - rail, size - gate_r, rail))  # bottom-right

    # Dashed cut-outs along the horizontal rails
    for x in range(8, size - 12, 14):
        pygame.draw.rect(img, hole, (x, 3, 9, 3))
    for x in range(8, gate_l - 8, 14):
        pygame.draw.rect(img, hole, (x, size - rail + 3, 9, 3))
    for x in range(gate_r + 6, size - 12, 14):
        pygame.draw.rect(img, hole, (x, size - rail + 3, 9, 3))

    # Gate posts
    pygame.draw.rect(img, fence_dark, (gate_l - 4, size - 22, 6, 22))
    pygame.draw.rect(img, fence_dark, (gate_r - 2, size - 22, 6, 22))
    pygame.draw.rect(img, fence_dark, (gate_l, size - 26, gate_r - gate_l, 5))  # arch bar

    # --- House ---
    pygame.draw.rect(img, (246, 175, 69), (18, 42, 54, 36))               # walls
    pygame.draw.polygon(img, (216, 38, 85),                               # roof
                        [(11, 44), (28, 20), (62, 20), (79, 44)])
    pygame.draw.rect(img, (200, 125, 40), (38, 54, 12, 24))               # door
    pygame.draw.rect(img, (246, 175, 69), (41, 57, 6, 21))                # door inset

    return pygame.transform.scale(
        img, (size * FARM_SCALE, size * FARM_SCALE)
    )   # nearest-neighbour keeps it crisp

def van_geometry() -> tuple[pygame.Rect, pygame.Rect, float]:
    """Return (trailer_rect, inside_rect, scale) for the van interior.

    Same look as the van in farm.py (358 x 142 trailer), but never shorter
    than a track-sized horse needs to stand in it.
    """
    w = int(C.WIDTH * 0.8)
    k = w / 358
    b = max(4, int(8 * k))
    horse_h = (133 + C.MAX_LEG_LENGTH + 40) * C.SCALE      # torso + longest leg + head room
    h = max(int(142 * k), int(horse_h) + 2 * b)
    trailer = pygame.Rect(0, 0, w, h)
    trailer.center = (C.WIDTH // 2, int(C.HEIGHT * 0.45))
    inside = trailer.inflate(-2 * b, -2 * b)
    return trailer, inside, k


def draw_van_interior(screen: pygame.Surface, dim: pygame.Surface) -> None:
    """Dim the world and draw the empty van trailer, styled like farm.py."""
    screen.blit(dim, (0, 0))
    trailer, inside, k = van_geometry()

    # Truck bed under the trailer
    bed = pygame.Rect(trailer.left + int(73 * k), trailer.bottom - int(27 * k),
                      int(130 * k), int(32 * k))
    pygame.draw.rect(screen, VAN_BED, bed)

    # Trailer: light-blue border, white inside
    pygame.draw.rect(screen, VAN_BORDER, trailer)
    pygame.draw.rect(screen, VAN_FILL, inside)

    # Wheels
    for dx in (103, 163):
        c = (trailer.left + int(dx * k), trailer.bottom + int(6 * k))
        pygame.draw.circle(screen, WHEEL, c, int(22 * k))
        pygame.draw.circle(screen, HUB, c, int(7 * k))


def near_farm(player, farm_rect: pygame.Rect) -> bool:
    """True when the player is close to the farm's gate (bottom-centre)."""
    gate_x, gate_y = farm_rect.centerx, farm_rect.bottom
    return math.hypot(player.x - gate_x, player.y - gate_y) <= FARM_INTERACT_DIST


def draw_player_money(screen, money_font):
    """Draws the current money amount flush against the top-left corner with only the bottom-right corner rounded."""
    money_text = f"${track.player_money}"
    
    m_surf = money_font.render(money_text, True, (30, 160, 50))
    
    box_w = m_surf.get_width() + C.s(18) * 2
    box_h = m_surf.get_height() + C.s(12) * 2
    
    box_rect = pygame.Rect(-C.s(4), -C.s(4), box_w + C.s(4), box_h + C.s(4))
    
    pygame.draw.rect(
        screen, 
        (255, 255, 255), 
        box_rect, 
        border_bottom_right_radius=C.s(14)
    )
    pygame.draw.rect(
        screen, 
        (60, 60, 60), 
        box_rect, 
        max(1, C.s(2)), 
        border_bottom_right_radius=C.s(14)
    )
    
    screen.blit(m_surf, (C.s(14), C.s(8)))


# ============================================================
# WORLD ENTRY POINT
# ============================================================

def run_world() -> None:
    """Run the overworld loop until the player quits."""

    # --- Screen setup ---
    screen = get_screen()
    pygame.display.set_caption("Horse Racing World")
    clock  = pygame.time.Clock()

    # --- Static world decorations (seeded for reproducibility) ---
    random.seed(12)

    grass_details = [
        (
            random.randint(0, C.WORLD_WIDTH),
            random.randint(0, C.WORLD_HEIGHT),
            random.choice([C.DARK_GRASS, C.LIGHT_GRASS, C.GRASS]),
        )
        for _ in range(900)
    ]

    flowers = [
        (
            random.randint(0, C.WORLD_WIDTH),
            random.randint(0, C.WORLD_HEIGHT),
            random.choice([(255,225,130), (245,170,180), (230,230,245)]),
        )
        for _ in range(100)
    ]

    random.seed()   # back to random seed for gameplay

    # --- Build static sprites (once) ---
    track_sprite = build_race_track_sprite()
    track_rect   = pygame.Rect(660, 280, 620, 460)

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
    player = Player(x=300.0, y=450.0)
    lasso  = Lasso()
    van    = Van()
    pen_horses: list[WorldHorse] = []   # horses living in the farm pen

    # Spawn world horses
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
            if not h.can_stand(test_x, test_y, horse_obstacles):
                continue
            if (test_x - player.x) ** 2 + (test_y - player.y) ** 2 < 400 ** 2:
                continue
            h.x = float(test_x)
            h.y = float(test_y)
            break

        horse_start_state[id(h)] = h.state
        horses.append(h)

    # --- Camera ---
    camera_x, camera_y = update_camera(player.x, player.y)

    # --- Fonts ---
    font         = get_font(24, bold=True)
    small_font   = get_font(17)
    title_font   = get_font(30, bold=True)
    money_font   = get_font(C.s(28), bold=True)

    # Dark overlay shown behind the van interior
    van_dim = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    van_dim.fill((0, 0, 0, 120))

    # Van physics: caught horses are simulated like the race horses
    van_trailer, van_inside, _ = van_geometry()
    van_space   = ragdoll.create_space()
    ragdoll.add_box_walls(van_space, van_inside)
    van_horses: dict[int, ragdoll.Ragdoll] = {}   # id(world horse) -> VanRagdoll
    van_acc     = 0.0
    drag        = {"vh": None, "ox": 0.0, "oy": 0.0, "last": None}
    sel         = {"vh": None}   # horse whose stats panel is showing (right-click)

    def freeze(rag: RaceHorse) -> None:
        """Zero all motion on a horse (used when grabbing / dropping it)."""
        rag.torso.velocity = (0, 0)
        rag.torso.angular_velocity = 0
        rag.head.body.velocity = (0, 0)
        rag.head.body.angular_velocity = 0
        rag.head.stop()
        rag.tail.body.velocity = (0, 0)
        rag.tail.body.angular_velocity = 0
        rag.tail.stop()
        for leg in rag.legs:
            leg.body.velocity = (0, 0)
            leg.body.angular_velocity = 0
            leg.stop()

    def cancel_drag() -> None:
        sel["vh"] = None
        if drag["vh"] is not None:
            freeze(drag["vh"].race)
        drag["vh"], drag["last"] = None, None

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


    running = True

    while running:
        dt = min(clock.tick(C.FPS_WORLD) / 1000.0, 0.05)
        mouse_pos = pygame.mouse.get_pos()

        # --------------------------------------------------------
        # EVENTS
        # --------------------------------------------------------
        for event in pygame.event.get():

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
                    if player.near_track(track_rect):
                        run_track()
                        # Restore world display after the race
                        screen = get_screen()
                        pygame.display.set_caption("Horse Racing World")
                        clock  = pygame.time.Clock()

                    elif near_farm(player, farm_rect):
                        run_farm(van.inventory, pen_horses)
                        # Restore world display after the farm
                        screen = get_screen()
                        pygame.display.set_caption("Horse Racing World")
                        clock  = pygame.time.Clock()

                    elif near_house(player, house_rect):
                        caught_horses = list(dict.fromkeys(van.inventory))

                        def sell_caught_horse(horse: WorldHorse, payout: int) -> None:
                            for collection in (van.inventory, horses):
                                if horse in collection:
                                    collection.remove(horse)
                            horse_start_state.pop(id(horse), None)
                            track.player_money += payout

                        run_scale_house(caught_horses, on_sold=sell_caught_horse)
                        screen = get_screen()
                        pygame.display.set_caption("Horse Racing World")
                        clock  = pygame.time.Clock()

                    elif near_shop(player, shop_rect):
                        run_shop()
                        # Restore world display after the shop
                        screen = get_screen()
                        pygame.display.set_caption("Horse Racing World")
                        clock  = pygame.time.Clock()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if van.open:
                    # Grab a horse in the van
                    if drag["vh"] is None:
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
                    lasso.throw(player.x, player.y, target_x, target_y)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and van.open:
                # Right-click a horse in the van to show its stats
                hit = None
                for vh in reversed(list(van_horses.values())):
                    if vh.race.rect().collidepoint(event.pos):
                        hit = vh
                        break
                sel["vh"] = None if hit is sel["vh"] else hit

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and drag["vh"] is not None:
                vh = drag["vh"]
                freeze(vh.race)
                drag["vh"], drag["last"] = None, None
                van_acc = 0.0
                if not van_trailer.collidepoint(event.pos):
                    release_to_world(vh)      # dropped outside the van -> back to the world

        # --------------------------------------------------------
        # UPDATE
        # --------------------------------------------------------
        if not van.open:
            keys = pygame.key.get_pressed()
            player.update(keys)

        lasso.update(horses, player.x, player.y)

        # Add freshly caught horses to van
        for h in horses:
            if h.state == "caught" and h not in van.inventory and h not in pen_horses:
                van.add(h)

        for h in horses:
            if not h.traits.get("dead", False):
                h.update(horse_obstacles)

        camera_x, camera_y = update_camera(player.x, player.y)

        # --------------------------------------------------------
        # DRAW
        # --------------------------------------------------------
        draw_grass(screen, camera_x, camera_y, grass_details, flowers)
        draw_race_track(screen, track_sprite, track_rect, camera_x, camera_y)

        # Farm, House, and Shop buildings (transparent background, grass shows through)
        screen.blit(farm_sprite, (farm_rect.x - camera_x, farm_rect.y - camera_y))
        screen.blit(house_sprite, (house_rect.x - camera_x, house_rect.y - camera_y))
        screen.blit(shop_sprite, (shop_rect.x - camera_x, shop_rect.y - camera_y))

        draw_world_characters(screen, player, horses, camera_x, camera_y)

        lasso.draw(screen, player.x, player.y, camera_x, camera_y)

        # Interaction prompt
        prompt_text = None
        if not van.open:
            if player.near_track(track_rect):
                prompt_text = "Press E to enter the race track"
            elif near_farm(player, farm_rect):
                prompt_text = "Press E to enter the farm"
            elif near_house(player, house_rect):
                prompt_text = "Press E to enter Glue"
            elif near_shop(player, shop_rect):
                prompt_text = "Press E to enter the shop"

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
                        # Ensure dead traits disable motor/limits instantly inside the van too
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

            if sel["vh"] is not None and not sel["vh"].world_horse.traits.get("dead", False):
                ragdoll.draw_stats_panel(screen, sel["vh"].race, sel["vh"].world_horse.traits)

        # Draw Clean Money Display on Top Left
        draw_player_money(screen, money_font)

        pygame.display.flip()