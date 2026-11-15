"""farm_art.py — The farm's look and layout.

Everything the farm scene draws (sky, grass, house, shed, van, pen fence) plus
the base-resolution zones that decide where a horse counts as being. The scene
scales the 742 x 419 base art up to the current screen.
"""

import random

import pygame

from game import constants as C

BASE_W, BASE_H = 742, 419

SKY        = (130, 200, 245)
GROUND     = (255, 255, 130)
FENCE      = (255, 170, 50)
FENCE_DARK = (230, 140, 30)
HOUSE      = (245, 165, 75)
HOUSE_DARK = (215, 130, 45)
ROOF       = (225, 125, 35)
WINDOW     = (255, 240, 200)
SHED_ROOF  = (190, 100, 40)
SHED_LIGHT = (240, 160, 60)
SHED_WALL  = (205, 115, 45)
SHED_IN    = (165, 85, 35)


def _draw_fence(surf: pygame.Surface, rect: pygame.Rect) -> None:
    """Orange wooden fence enclosing `rect`."""
    t = 6

    for y in (rect.top, rect.top + 18, rect.bottom - 28, rect.bottom - 10):
        pygame.draw.rect(surf, FENCE, (rect.left, y, rect.width, t))

    for x in (rect.left, rect.right - t):
        pygame.draw.rect(surf, FENCE, (x, rect.top, t, rect.height))

    for x in range(rect.left, rect.right, 44):
        pygame.draw.rect(surf, FENCE_DARK, (x, rect.top - 2, 8, 28))
        pygame.draw.rect(surf, FENCE_DARK, (x, rect.bottom - 32, 8, 28))

    pygame.draw.rect(surf, FENCE_DARK, (rect.right - 8, rect.top - 2, 8, 28))
    pygame.draw.rect(surf, FENCE_DARK, (rect.right - 8, rect.bottom - 32, 8, 28))


def _draw_house(surf: pygame.Surface) -> None:
    pygame.draw.polygon(surf, ROOF, [(190, 26), (210, 0), (282, 0), (300, 26)])
    pygame.draw.rect(surf, HOUSE, (203, 26, 84, 34))
    pygame.draw.rect(surf, WINDOW, (216, 32, 16, 14))
    pygame.draw.rect(surf, WINDOW, (258, 32, 16, 14))
    pygame.draw.rect(surf, HOUSE_DARK, (216, 32, 16, 14), 2)
    pygame.draw.rect(surf, HOUSE_DARK, (258, 32, 16, 14), 2)

    for x, c in ((212, (235, 90, 130)), (224, (235, 90, 130)),
                 (262, (235, 90, 130)), (274, (235, 90, 130))):
        pygame.draw.rect(surf, (90, 170, 80), (x, 56, 6, 4))
        pygame.draw.rect(surf, c, (x + 1, 52, 4, 4))


def _draw_shed(surf: pygame.Surface) -> None:
    pygame.draw.rect(surf, SHED_WALL, (386, 78, 316, 126))
    pygame.draw.rect(surf, SHED_IN, (402, 88, 284, 108))
    pygame.draw.rect(surf, (140, 70, 25), (402, 190, 284, 8))
    pygame.draw.polygon(surf, SHED_ROOF, [(375, 84), (544, 0), (713, 84)])
    pygame.draw.polygon(surf, SHED_LIGHT, [(418, 70), (451, 53), (451, 70)])
    pygame.draw.polygon(surf, SHED_LIGHT, [(637, 53), (670, 70), (637, 70)])
    pygame.draw.rect(surf, SHED_ROOF, (375, 80, 338, 8))
    pygame.draw.rect(surf, (245, 205, 75), (394, 126, 8, 24))
    pygame.draw.circle(surf, (110, 65, 30), (398, 138), 2)


def _draw_van(surf: pygame.Surface) -> None:
    pygame.draw.rect(surf, C.VAN_BED, (445, 365, 130, 32))
    pygame.draw.rect(surf, C.VAN_BORDER, (372, 250, 358, 142))
    pygame.draw.rect(surf, C.VAN_FILL, (380, 258, 342, 126))

    for cx in (475, 535):
        pygame.draw.circle(surf, C.WHEEL, (cx, 398), 22)
        pygame.draw.circle(surf, C.HUB, (cx, 398), 7)


def _draw_grass(surf: pygame.Surface) -> None:
    """Grass ground with darker/lighter tufts and flowers."""
    rng = random.Random(7)
    sky_h = 66
    pygame.draw.rect(surf, C.GRASS, (0, sky_h, BASE_W, BASE_H - sky_h))

    for _ in range(300):
        x = rng.randint(0, BASE_W - 5)
        y = rng.randint(sky_h, BASE_H - 5)
        pygame.draw.rect(
            surf,
            rng.choice([C.DARK_GRASS, C.LIGHT_GRASS, C.GRASS]),
            (x, y, 5, 5),
        )

    for _ in range(10):
        x = rng.randint(0, BASE_W - 16)
        y = rng.randint(sky_h + 6, BASE_H - 14)
        pygame.draw.rect(surf, C.DARK_GRASS, (x, y, 14, 7))
        pygame.draw.rect(surf, C.LIGHT_GRASS, (x + 5, y + 7, 9, 5))

    for _ in range(45):
        x = rng.randint(0, BASE_W - 4)
        y = rng.randint(sky_h, BASE_H - 4)
        pygame.draw.rect(
            surf,
            rng.choice([(255, 225, 130), (245, 170, 180), (230, 230, 245)]),
            (x, y, 3, 3),
        )


def build_farm_scene() -> pygame.Surface:
    """Render the farm background."""
    surf = pygame.Surface((BASE_W, BASE_H))
    surf.fill(SKY)
    _draw_grass(surf)
    _draw_shed(surf)
    _draw_house(surf)
    _draw_van(surf)
    return surf


def build_fence_overlay() -> pygame.Surface:
    """The pen fence on a transparent surface."""
    surf = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
    _draw_fence(surf, pygame.Rect(14, 42, 310, 198))
    return surf


def build_shed_doors() -> pygame.Surface:
    """Draw the closed shed doors."""
    surf = pygame.Surface((BASE_W, BASE_H), pygame.SRCALPHA)
    pygame.draw.rect(surf, SHED_WALL, (402, 88, 284, 108))
    pygame.draw.rect(surf, (125, 62, 28), (402, 88, 284, 108), 5)
    pygame.draw.rect(surf, SHED_LIGHT, (406, 92, 134, 100))
    pygame.draw.rect(surf, SHED_LIGHT, (544, 92, 138, 100))
    pygame.draw.line(surf, SHED_WALL, (406, 92), (540, 192), 4)
    pygame.draw.line(surf, SHED_WALL, (540, 92), (406, 192), 4)
    pygame.draw.line(surf, SHED_WALL, (544, 92), (682, 192), 4)
    pygame.draw.line(surf, SHED_WALL, (682, 92), (544, 192), 4)
    pygame.draw.circle(surf, (110, 65, 30), (540, 142), 4)
    pygame.draw.circle(surf, (110, 65, 30), (548, 142), 4)
    return surf


# ============================================================
# ZONES  (base-resolution coordinates)
# ============================================================

PEN_ZONE = pygame.Rect(14, 42, 310, 198)
PEN_AREA = pygame.Rect(22, 50, 294, 176)
VAN_ZONE = pygame.Rect(372, 250, 358, 142)
VAN_AREA = pygame.Rect(382, 258, 338, 126)
SHED_ZONE = pygame.Rect(386, 78, 316, 126)
SHED_AREA = pygame.Rect(402, 88, 284, 108)
SHED_HANDLE_ZONE = pygame.Rect(392, 124, 14, 32)
SLEEP_BUTTON_ZONE = pygame.Rect(BASE_W - 90, 12, 78, 28)

BREEDING_TIME = 3.0
EAT_TIME = 1.2   # seconds the hay spins and shrinks at the mouth