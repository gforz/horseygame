"""glue_art.py — The scale house interior: treadmill, house front and the scale.

The horse is weighed by walking it up the treadmill into the dark opening; the
brass scale at the top left shows the total weight of whatever stands on it.
"""

import math

import pygame

from game import constants as C
from game.constants import HUB, VAN_BED, VAN_BORDER, VAN_FILL, WHEEL
from game.gfx.fonts import get_font

BACKGROUND = (144, 54, 54)

ORANGE = (221, 120, 45)
BELT_BLACK = (17, 10, 5)
WALL_PINK = (200, 60, 90)
CORNER_ROOF = (132, 43, 57)


def belt_height(rect: pygame.Rect) -> int:
    return max(16, round(rect.height * 0.6))


def belt_y(rect: pygame.Rect) -> int:
    """Walking surface: the top edge of the belt."""
    return rect.top


def treadmill_layout(rect: pygame.Rect) -> dict:
    """Shared geometry for the belt and the door/house it runs into."""
    belt_h = belt_height(rect)
    pillar_w = round(belt_h * 2.1)
    opening_w = round(belt_h * 4.3)
    wall_w = round(belt_h * 3.1)
    belt_bottom = rect.top + belt_h
    wall_left = rect.right - wall_w
    right_pillar = pygame.Rect(wall_left - pillar_w, 0, pillar_w, belt_bottom)
    opening = pygame.Rect(right_pillar.left - opening_w, 0, opening_w, rect.top)
    left_pillar = pygame.Rect(opening.left - pillar_w, 0, pillar_w, belt_bottom)
    return {
        "belt_h": belt_h,
        "wall_w": wall_w,
        "wall_left": wall_left,
        "left_pillar": left_pillar,
        "opening": opening,
        "right_pillar": right_pillar,
    }


def draw_treadmill(screen: pygame.Surface, rect: pygame.Rect, phase: float = 0.0) -> None:
    """Draw fixed, rotating poles with a chain of links looping around them."""
    layout = treadmill_layout(rect)
    belt_h = layout["belt_h"]

    pole_gray = (170, 170, 170)
    pole_dark = (125, 125, 125)
    spoke_color = (70, 70, 70)
    chain_color = (150, 150, 150)

    belt = pygame.Rect(rect.left, rect.top, layout["right_pillar"].left - rect.left, belt_h)
    pygame.draw.rect(screen, BELT_BLACK, belt)

    link_h = max(2, belt_h // 8)
    link_len = max(4, belt_h // 4)
    path_r = belt_h / 2 - link_h / 2
    pole_r = max(4, round(path_r * 0.8))
    center_y = belt.centery
    left_x = belt.left + belt_h / 2
    right_x = belt.right - belt_h / 2

    spacing = belt_h * 1.55
    pole_count = max(2, round((right_x - left_x) / spacing) + 1)
    spin = phase / path_r
    for index in range(pole_count):
        x = round(left_x + (right_x - left_x) * index / (pole_count - 1))
        pygame.draw.circle(screen, pole_gray, (x, center_y), pole_r)
        pygame.draw.circle(screen, pole_dark, (x, center_y), max(2, pole_r // 2))
        for offset in (0.0, math.pi):
            angle = spin + offset
            end = (
                round(x + math.cos(angle) * pole_r * 0.85),
                round(center_y + math.sin(angle) * pole_r * 0.85),
            )
            pygame.draw.line(screen, spoke_color, (x, center_y), end, max(1, pole_r // 5))
        pygame.draw.circle(screen, pole_gray, (x, center_y), max(1, pole_r // 4))

    def draw_link(x: float, y: float, angle: float) -> None:
        half_length = link_len / 2
        half_height = link_h / 2
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        corners = []
        for along, across in (
            (-half_length, -half_height),
            (half_length, -half_height),
            (half_length, half_height),
            (-half_length, half_height),
        ):
            corners.append((
                round(x + along * cos_a - across * sin_a),
                round(y + along * sin_a + across * cos_a),
            ))
        pygame.draw.polygon(screen, chain_color, corners)

    straight = right_x - left_x
    arc = math.pi * path_r
    loop = 2 * straight + 2 * arc
    link_count = max(8, round(loop / (link_len * 2)))
    pitch = loop / link_count
    for index in range(link_count):
        distance = (phase + index * pitch) % loop
        if distance < straight:
            draw_link(left_x + distance, center_y - path_r, 0.0)
        elif distance < straight + arc:
            theta = -math.pi / 2 + (distance - straight) / path_r
            draw_link(
                right_x + math.cos(theta) * path_r,
                center_y + math.sin(theta) * path_r,
                theta + math.pi / 2,
            )
        elif distance < 2 * straight + arc:
            offset = distance - straight - arc
            draw_link(right_x - offset, center_y + path_r, math.pi)
        else:
            theta = math.pi / 2 + (distance - 2 * straight - arc) / path_r
            draw_link(
                left_x + math.cos(theta) * path_r,
                center_y + math.sin(theta) * path_r,
                theta + math.pi / 2,
            )


def draw_house_behind_treadmill(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw only the left pillar and black box behind the treadmill and horses."""
    layout = treadmill_layout(rect)
    pygame.draw.rect(screen, ORANGE, layout["left_pillar"])
    pygame.draw.rect(screen, BELT_BLACK, layout["opening"])


def draw_house_front(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw the whole pink wall section, right pillar and corner in front of the horses."""
    layout = treadmill_layout(rect)
    belt_bottom = rect.top + layout["belt_h"]
    wall_left = layout["wall_left"]

    # Upper/main pink wall section
    pygame.draw.polygon(
        screen,
        WALL_PINK,
        [
            (wall_left, 0),
            (rect.right, 0),
            (rect.right, belt_bottom - layout["wall_w"]),
            (wall_left, belt_bottom),
        ],
    )
    # Right pillar
    pygame.draw.rect(screen, ORANGE, layout["right_pillar"])

    # Bottom-right angled corner roof piece
    corner_poly = [
        (wall_left, belt_bottom),
        (rect.right, belt_bottom),
        (rect.right, belt_bottom - layout["wall_w"]),
    ]
    pygame.draw.polygon(screen, CORNER_ROOF, corner_poly)


def draw_treadmill_label(screen: pygame.Surface, layout: dict,
                         treadmill_rect: pygame.Rect) -> None:
    """"5 dollars for 100 lbs" painted on the wall above the treadmill."""
    label_font = get_font(max(18, C.s(24)), bold=True)
    color = tuple(channel * 2 // 3 for channel in BACKGROUND)
    label = label_font.render("5 dollars for 100 lbs", True, color)
    screen.blit(
        label,
        label.get_rect(
            bottomright=(
                layout["left_pillar"].left - max(16, C.s(20)),
                treadmill_rect.top - max(100, C.s(120)),
            )
        ),
    )


def draw_scale(screen: pygame.Surface, scale_art: pygame.Surface,
               scale_factor: float, scale_top: int,
               on_scale: bool, total_weight: int) -> None:
    """Redraw the brass scale face and stamp it, with the weight readout."""
    scale_art.fill((0, 0, 0, 0))
    pygame.draw.rect(scale_art, (55, 53, 51), (12, 3, 214, 36))
    pygame.draw.rect(scale_art, (205, 207, 201), (15, 6, 208, 29))
    pygame.draw.rect(scale_art, (239, 238, 224), (18, 8, 202, 15))
    scale_left, scale_right = 18, 220
    for tick in range(31):
        x = scale_left + (scale_right - scale_left) * tick // 30
        major = tick % 10 == 0
        pygame.draw.line(scale_art, (45, 45, 43), (x, 24), (x, 31 if major else 28), 1)

    pygame.draw.rect(scale_art, (158, 158, 154), (106, 39, 20, 84))
    pygame.draw.rect(scale_art, (41, 39, 38), (62, 122, 111, 8))
    pygame.draw.rect(scale_art, (152, 151, 145), (70, 130, 95, 8))

    if on_scale:
        marker_x = scale_left + int(
            (scale_right - scale_left) * min(total_weight, 3000) / 3000
        )
        pygame.draw.line(scale_art, (179, 33, 42), (marker_x, 23), (marker_x, 32), 2)

    scale_size = (
        max(1, int(scale_art.get_width() * scale_factor)),
        max(1, int(scale_art.get_height() * scale_factor)),
    )
    screen.blit(pygame.transform.scale(scale_art, scale_size), (0, scale_top))

    label_font = pygame.font.SysFont("Arial", max(10, round(7 * scale_factor)), bold=True)
    for label, x in (("1000", 81), ("2000", 146), ("3000", 199)):
        text = label_font.render(label, True, (30, 30, 29))
        screen.blit(
            text,
            text.get_rect(center=(round(x * scale_factor), scale_top + round(17 * scale_factor))),
        )

    if on_scale:
        weight_font = pygame.font.SysFont(
            "Arial", max(16, round(10 * scale_factor)), bold=True
        )
        weight_text = weight_font.render(
            f"Weight: {total_weight:,} lb", True, (255, 245, 225)
        )
        screen.blit(
            weight_text,
            (min(scale_size[0] + max(12, round(8 * scale_factor)),
                 screen.get_width() - weight_text.get_width() - 12),
             scale_top + max(12, round(10 * scale_factor))),
        )


def draw_van(screen: pygame.Surface, rect: pygame.Rect) -> None:
    """Draw the farm-style trailer body behind its physics horses."""
    van = pygame.Surface((358, 170), pygame.SRCALPHA)
    pygame.draw.rect(van, VAN_BED, (73, 115, 130, 32))
    pygame.draw.rect(van, VAN_BORDER, (0, 0, 358, 142))
    pygame.draw.rect(van, VAN_FILL, (8, 8, 342, 126))
    for x in (103, 163):
        pygame.draw.circle(van, WHEEL, (x, 148), 22)
        pygame.draw.circle(van, HUB, (x, 148), 7)
    screen.blit(pygame.transform.scale(van, rect.size), rect.topleft)