"""world_map.py — The overworld's buildings and the van trailer.

Builds the transparent pixel-art sprites for the farm, the shop and the scale
house, places them in the world, and answers "is the player close enough to
walk in?". Also owns the van trailer geometry used by the van overlay.
"""

import math

import pygame

from game import constants as C
from game.constants import VAN_BED, VAN_BORDER, VAN_FILL, HUB, WHEEL

# ============================================================
# FARM
# ============================================================

FARM_SCALE         = 2           # sprite is drawn at 130x130 -> 260x260 in the world
FARM_POS           = (120, 130)  # top-left of the farm in world coordinates
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
SHOP_POS           = (1500, 180) # top-left of the shop in world coordinates
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

HOUSE_POSITION = (1850, 420)
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