"""world_map.py — The overworld's buildings and the van trailer.

Builds the transparent pixel-art sprites for the farm, the shop and the scale
house, places them in the world, and answers "is the player close enough to
walk in?". Also owns the van trailer geometry used by the van overlay.
"""

import math

import pygame

from game import constants as C
from game.constants import VAN_BED, VAN_BORDER, VAN_FILL, HUB, WHEEL
from game.gfx.fonts import get_font


# ============================================================
# WORLD MAP OVERLAY
# ============================================================

def draw_world_map(
    screen: pygame.Surface,
    player,
    track_rect: pygame.Rect,
    farm_rect: pygame.Rect,
    house_rect: pygame.Rect,
    shop_rect: pygame.Rect,
    nighttime: bool,
) -> None:
    """Draw a full-world overview with labelled points of interest."""
    overlay = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    overlay.fill((18, 24, 20, 220))
    screen.blit(overlay, (0, 0))

    panel_w = min(C.WIDTH - C.s(40), C.s(1700))
    panel_h = min(C.HEIGHT - C.s(40), C.s(980))
    panel = pygame.Rect(
        (C.WIDTH - panel_w) // 2,
        (C.HEIGHT - panel_h) // 2,
        panel_w,
        panel_h,
    )
    pygame.draw.rect(screen, (48, 74, 48), panel, border_radius=C.s(18))
    pygame.draw.rect(screen, C.GOLD, panel, C.s(4), border_radius=C.s(18))

    title = get_font(C.s(34), bold=True).render("World Map", True, C.WORLD_WHITE)
    screen.blit(title, title.get_rect(midtop=(panel.centerx, panel.top + C.s(18))))

    padding = C.s(30)
    map_top = panel.top + C.s(78)
    map_bottom = panel.bottom - C.s(52)
    map_rect = pygame.Rect(
        panel.left + padding,
        map_top,
        panel.width - padding * 2,
        map_bottom - map_top,
    )

    pygame.draw.rect(screen, C.GRASS, map_rect, border_radius=C.s(10))
    pygame.draw.rect(screen, (205, 190, 125), map_rect, C.s(3), border_radius=C.s(10))

    scale_x = map_rect.width / C.WORLD_WIDTH
    scale_y = map_rect.height / C.WORLD_HEIGHT

    def world_to_map(x: float, y: float) -> tuple[int, int]:
        return (
            int(map_rect.left + x * scale_x),
            int(map_rect.top + y * scale_y),
        )

    # Simple dirt roads help the POIs read as part of one connected world.
    road = (190, 155, 95)
    track_pos = world_to_map(track_rect.centerx, track_rect.centery)
    farm_pos = world_to_map(farm_rect.centerx, farm_rect.centery)
    shop_pos = world_to_map(shop_rect.centerx, shop_rect.centery)
    house_pos = world_to_map(house_rect.centerx, house_rect.centery)
    pygame.draw.line(screen, road, farm_pos, track_pos, max(3, C.s(12)))
    pygame.draw.line(screen, road, track_pos, shop_pos, max(3, C.s(12)))
    pygame.draw.line(screen, road, shop_pos, house_pos, max(3, C.s(12)))

    # Map grid.
    grid_color = (76, 145, 70)
    for i in range(1, 8):
        x = map_rect.left + map_rect.width * i // 8
        pygame.draw.line(screen, grid_color, (x, map_rect.top), (x, map_rect.bottom), 1)
    for i in range(1, 5):
        y = map_rect.top + map_rect.height * i // 5
        pygame.draw.line(screen, grid_color, (map_rect.left, y), (map_rect.right, y), 1)

    pois = (
        ("Race Track", track_pos, (225, 150, 60), None),
        ("Farm", farm_pos, (255, 215, 90), None),
        ("Shop", shop_pos, (230, 120, 70), "Closed" if nighttime else None),
        ("Glue", house_pos, (130, 190, 220), "Closed" if nighttime else None),
    )

    marker_radius = max(8, C.s(16))
    label_font = get_font(C.s(20), bold=True)
    state_font = get_font(C.s(15), bold=True)

    for name, pos, color, status in pois:
        pygame.draw.circle(screen, C.DARK_BROWN, pos, marker_radius + C.s(4))
        pygame.draw.circle(screen, color, pos, marker_radius)
        pygame.draw.circle(screen, C.WORLD_WHITE, pos, marker_radius, max(2, C.s(3)))
        label = label_font.render(name, True, C.WORLD_WHITE)
        label_x = pos[0] + marker_radius + C.s(8)
        label_y = pos[1] - label.get_height() // 2
        if label_x + label.get_width() > map_rect.right:
            label_x = pos[0] - marker_radius - C.s(8) - label.get_width()
        label_bg = label.get_rect(topleft=(label_x, label_y)).inflate(C.s(12), C.s(8))
        pygame.draw.rect(screen, (35, 55, 35), label_bg, border_radius=C.s(7))
        screen.blit(label, label.get_rect(center=label_bg.center))
        if status:
            status_surf = state_font.render(status, True, (255, 170, 170))
            status_rect = status_surf.get_rect(midtop=(pos[0], pos[1] + marker_radius + C.s(4)))
            pygame.draw.rect(
                screen,
                (70, 45, 45),
                status_rect.inflate(C.s(8), C.s(4)),
                border_radius=C.s(5),
            )
            screen.blit(status_surf, status_rect)

    player_pos = world_to_map(player.x, player.y)
    pygame.draw.circle(screen, C.DARK_BROWN, player_pos, max(9, C.s(18)))
    pygame.draw.circle(screen, (70, 190, 255), player_pos, max(6, C.s(12)))
    pygame.draw.circle(screen, C.WORLD_WHITE, player_pos, max(2, C.s(5)))

    hint = get_font(C.s(18), bold=True).render("Press M or Esc to close", True, C.WORLD_WHITE)
    screen.blit(hint, hint.get_rect(midbottom=(panel.centerx, panel.bottom - C.s(12))))

# ============================================================
# FARM
# ============================================================

FARM_SCALE         = 2           # sprite is drawn at 130x130 -> 260x260 in the world
FARM_POS           = (
    C.WORLD_WIDTH * 72 // 100 - 130 * FARM_SCALE // 2,
    C.WORLD_HEIGHT * 28 // 100 - 130 * FARM_SCALE // 2,
)
FARM_INTERACT_DIST = 120         # how close the player must be to the gate


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


def near_farm(player, farm_rect: pygame.Rect) -> bool:
    """True when the player is close to the farm's gate (bottom-centre)."""
    gate_x, gate_y = farm_rect.centerx, farm_rect.bottom
    return math.hypot(player.x - gate_x, player.y - gate_y) <= FARM_INTERACT_DIST


# ============================================================
# SHOP
# ============================================================

SHOP_SCALE         = 6           # scale factor to make it crisp and well-sized in the world
SHOP_POS           = (C.WORLD_WIDTH // 2 + 900, C.WORLD_HEIGHT // 2 - 54)
SHOP_INTERACT_DIST = 120         # how close the player must be to enter the shop


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


# ============================================================
# SCALE HOUSE  (Glue)
# ============================================================

HOUSE_POSITION = (C.WORLD_WIDTH // 2 + 2000, C.WORLD_HEIGHT // 2 - 77)
HOUSE_INTERACT_DIST = 150


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


# ============================================================
# VAN TRAILER
# ============================================================

def van_geometry() -> tuple[pygame.Rect, pygame.Rect, float]:
    """Return (trailer_rect, inside_rect, scale) for the van interior.

    Same look as the van in the farm (358 x 142 trailer), but never shorter
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
    """Dim the world and draw the empty van trailer, styled like the farm's."""
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