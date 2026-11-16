"""world_art.py — Overworld ground, camera maths and the player's vehicle.

The ground (grass, tufts, flowers) never changes, so it is rendered into
cached chunks and blitted instead of drawing its details every frame.
"""

import random
from collections import OrderedDict

import pygame

from game import constants as C

# Darker/lighter grass patches, at fixed world positions.
TUFT_PATCHES = [
    (200,200),(450,350),(900,700),(1200,400),
    (1500,800),(700,850),(300,750),(1600,250),
]

GROUND_CHUNK_SIZE = 1024
GROUND_CACHE_CHUNKS = 24
GROUND_TUFT_COUNT = 3600
TUFT_DARK_COLOR = (89, 165, 75)
TUFT_LIGHT_COLOR = (108, 190, 92)


class GroundMap:
    """Lazily rendered, cached chunks of the static overworld ground."""

    def __init__(self, flowers: list):
        self.chunks: OrderedDict[tuple[int, int], pygame.Surface] = OrderedDict()
        self.details_by_chunk: dict[tuple[int, int], list] = {}

        details_with_sizes = []
        details_with_sizes.extend(
            (x, y, TUFT_DARK_COLOR, 24, 12) for x, y in TUFT_PATCHES
        )
        details_with_sizes.extend(
            (x + 8, y + 12, TUFT_LIGHT_COLOR, 16, 8) for x, y in TUFT_PATCHES
        )
        tuft_random = random.Random(12)
        for _ in range(GROUND_TUFT_COUNT):
            x = tuft_random.randrange(C.WORLD_WIDTH - 24)
            y = tuft_random.randrange(C.WORLD_HEIGHT - 20)
            details_with_sizes.append((x, y, TUFT_DARK_COLOR, 24, 12))
            details_with_sizes.append((x + 8, y + 12, TUFT_LIGHT_COLOR, 16, 8))

        details_with_sizes.extend((x, y, color, 6, 6) for x, y, color in flowers)
        for item in details_with_sizes:
            x, y, _, width, height = item
            first_x = max(0, x) // GROUND_CHUNK_SIZE
            first_y = max(0, y) // GROUND_CHUNK_SIZE
            last_x = min(C.WORLD_WIDTH - 1, x + width - 1) // GROUND_CHUNK_SIZE
            last_y = min(C.WORLD_HEIGHT - 1, y + height - 1) // GROUND_CHUNK_SIZE
            for chunk_y in range(first_y, last_y + 1):
                for chunk_x in range(first_x, last_x + 1):
                    self.details_by_chunk.setdefault((chunk_x, chunk_y), []).append(item)

    def _get_chunk(self, chunk_x: int, chunk_y: int) -> pygame.Surface:
        key = (chunk_x, chunk_y)
        chunk = self.chunks.get(key)
        if chunk is not None:
            self.chunks.move_to_end(key)
            return chunk

        x = chunk_x * GROUND_CHUNK_SIZE
        y = chunk_y * GROUND_CHUNK_SIZE
        chunk = pygame.Surface((
            min(GROUND_CHUNK_SIZE, C.WORLD_WIDTH - x),
            min(GROUND_CHUNK_SIZE, C.WORLD_HEIGHT - y),
        ))
        chunk.fill(C.GRASS)
        for detail_x, detail_y, color, width, height in self.details_by_chunk.get(key, ()):
            pygame.draw.rect(
                chunk, color,
                (detail_x - x, detail_y - y, width, height),
            )

        self.chunks[key] = chunk
        if len(self.chunks) > GROUND_CACHE_CHUNKS:
            self.chunks.popitem(last=False)
        return chunk


def world_to_screen(x: float, y: float,
                    camera_x: float, camera_y: float) -> tuple:
    return int(x - camera_x), int(y - camera_y)


def screen_to_world(sx: float, sy: float,
                    camera_x: float, camera_y: float) -> tuple:
    return sx + camera_x, sy + camera_y


def update_camera(car_x: float, car_y: float) -> tuple:
    """Return (camera_x, camera_y) centred on the player."""
    cx = max(0, min(C.WORLD_WIDTH  - C.WIDTH,  car_x - C.WIDTH  // 2))
    cy = max(0, min(C.WORLD_HEIGHT - C.HEIGHT, car_y - C.HEIGHT // 2))
    return cx, cy


# ============================================================
# GROUND
# ============================================================

def build_ground(flowers: list) -> GroundMap:
    """Index the static ground details for on-demand chunk rendering."""
    return GroundMap(flowers)


def draw_ground(screen: pygame.Surface, ground: GroundMap,
                camera_x: float, camera_y: float) -> None:
    """Blit cached ground chunks covering the camera's view."""
    left = max(0, int(camera_x))
    top = max(0, int(camera_y))
    right = min(C.WORLD_WIDTH, left + C.WIDTH)
    bottom = min(C.WORLD_HEIGHT, top + C.HEIGHT)
    first_x = left // GROUND_CHUNK_SIZE
    first_y = top // GROUND_CHUNK_SIZE
    last_x = (right - 1) // GROUND_CHUNK_SIZE
    last_y = (bottom - 1) // GROUND_CHUNK_SIZE

    for chunk_y in range(first_y, last_y + 1):
        for chunk_x in range(first_x, last_x + 1):
            chunk = ground._get_chunk(chunk_x, chunk_y)
            screen.blit(
                chunk,
                (
                    chunk_x * GROUND_CHUNK_SIZE - int(camera_x),
                    chunk_y * GROUND_CHUNK_SIZE - int(camera_y),
                ),
            )


# ============================================================
# VEHICLE SPRITE
# ============================================================

def build_vehicle_sprite(flip: bool = False) -> pygame.Surface:
    """Pixel-art horse van, optionally mirrored to face left."""
    grid = [[None] * C.SPRITE_COLS for _ in range(C.SPRITE_ROWS)]

    def fill(c0, r0, c1, r1, color):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = color

    # Trailer
    fill(0,0,21,0,  C.V_TURQUOISE); fill(0,1,22,1, C.V_TURQUOISE)
    fill(0,2,23,2,  C.V_TURQUOISE); fill(0,3,24,3, C.V_TURQUOISE)
    fill(0,4,25,12, C.V_TURQUOISE)
    for wc in (3, 10, 16):
        fill(wc,3,wc+2,3, C.V_WINDOW)

    # Truck body
    fill(19,8,35,8, C.V_RED); fill(19,9,36,9,  C.V_RED)
    fill(19,10,37,11,C.V_RED);fill(19,12,36,12,C.V_RED)

    # Cab
    fill(28,4,30,4, C.V_RED);    fill(27,5,27,5, C.V_RED)
    fill(28,5,30,5, C.V_WINDOW); fill(31,5,31,5, C.V_RED)
    fill(27,6,27,6, C.V_RED);    fill(28,6,30,6, C.V_WINDOW)
    fill(31,6,32,6, C.V_RED);    fill(27,7,27,7, C.V_RED)
    fill(28,7,30,7, C.V_WINDOW); fill(31,7,33,7, C.V_RED)

    # Stripes
    fill(21,9,27,9,  C.V_YELLOW); fill(23,10,26,10,C.V_YELLOW)
    fill(31,9,34,9,  C.V_YELLOW); fill(30,10,33,10,C.V_YELLOW)

    # Wheels
    def wheel(c0):
        fill(c0+1,12,c0+2,12,C.V_BLACK)
        fill(c0,13,c0+3,14, C.V_BLACK)
        fill(c0+1,15,c0+2,15,C.V_BLACK)
        grid[13][c0+1] = C.V_GRAY
        grid[13][c0+2] = C.V_GRAY_LIGHT
        grid[14][c0+1] = C.V_GRAY_LIGHT
        grid[14][c0+2] = C.V_GRAY

    for wc in (1, 7, 22, 32):
        wheel(wc)

    surface = pygame.Surface(
        (C.SPRITE_COLS * C.CELL, C.SPRITE_ROWS * C.CELL), pygame.SRCALPHA
    )
    for r in range(C.SPRITE_ROWS):
        for c in range(C.SPRITE_COLS):
            color = grid[r][c]
            if color is not None:
                pygame.draw.rect(
                    surface, color,
                    (c * C.CELL, r * C.CELL, C.CELL, C.CELL),
                )

    if flip:
        surface = pygame.transform.flip(surface, True, False)
    return surface


# ============================================================
# DEPTH-SORTED WORLD DRAWING
# ============================================================

def draw_world_characters(screen: pygame.Surface,
                           player,          # Player instance
                           horses: list,    # list[WorldHorse]
                           camera_x: float,
                           camera_y: float) -> None:
    """Draw world horses and the player vehicle in y-sorted order."""
    items = [
        (h.y, h)
        for h in horses
        if h.state != "caught"
    ]
    items.append((player.feet_y, None))
    items.sort(key=lambda item: item[0])

    for _, obj in items:
        if obj is None:
            player.draw(screen, camera_x, camera_y)
        else:
            obj.draw(screen, camera_x, camera_y, C.WIDTH, C.HEIGHT)