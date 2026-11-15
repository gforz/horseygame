"""items.py — Buyable goods: hay sheaves and lassos.

Owns the pixel-art sprites, the one shared hay store (so the shop, the farm and
the van always see the same bales) and the small "is this bale in the van"
test used by every scene that draws one.
"""

import math

import pygame

# One shared store of hay dicts: {"rel_x", "rel_y", "location"} where location
# is "van" or "farm". Bales are the exact same dicts everywhere, so moving one
# in the farm is instantly visible in the shop and the van.
HAY: list[dict] = []


def sync_hay(*lists) -> list[dict]:
    """Merge hay dicts from any lists into the one shared store and return it."""
    for lst in lists:
        if lst is None or lst is HAY:
            continue
        for item in lst:
            if not any(item is known for known in HAY):
                HAY.append(item)
    return HAY


def hay_in_van(item: dict) -> bool:
    """Hay left loose on the farm (location == "farm") is not in the van."""
    return item.get("location", "van") != "farm"


def hay_sprite_scale(width: int) -> int:
    """Pixel scale that keeps a bale a sensible size on a `width` screen."""
    return max(2, int(width / 330))


# ============================================================
# HAY SPRITE
# ============================================================

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


# ============================================================
# LASSO SPRITE
# ============================================================

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