"""world_horse_sprite.py — The little side-on horse that wanders the overworld.

Rendered once per horse (at 4x, then scaled down) so the world can blit a
plain sprite instead of redrawing polygons every frame.
"""

import math
import random

import pygame

from game import constants as C
from game.gfx.horse_model import hoof_vertices, horse_body_geometry


def build_horse_sprite(traits: dict) -> pygame.Surface:
    color        = traits["color"]
    back_length  = traits["back_length"]
    front_length = traits["front_length"]
    back_hip_x   = traits["back_hip_x"]
    front_hip_x  = traits["front_hip_x"]
    start_angle  = traits["start_angle"]
    torso_length = traits.get("torso_length", C.DEFAULT_TORSO_LENGTH)
    torso_height = traits.get("torso_height", C.DEFAULT_TORSO_HEIGHT)

    ss = C.HORSE_SUPERSAMPLE
    k  = C.WORLD_HORSE_SCALE * ss

    hip_y = C.MODEL_CENTRE_Y + torso_height / 2
    theta = 0.0

    if C.TILT_UNEVEN_LEGS:
        theta = math.atan2(back_length - front_length, front_hip_x - back_hip_x)

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    pivot_x = C.MODEL_CENTRE_X
    pivot_y = hip_y

    canvas_size = int(800 * k)
    origin      = 100 * k

    big = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
    big.fill((color[0], color[1], color[2], 0))

    def pt(px, py):
        dx = px - pivot_x; dy = py - pivot_y
        rx = pivot_x + dx * cos_t - dy * sin_t
        ry = pivot_y + dx * sin_t + dy * cos_t
        return int(round(origin + rx * k)), int(round(origin + ry * k))

    def poly(c, points):
        pygame.draw.polygon(big, c, [pt(px, py) for px, py in points])

    def draw_world_leg(hip_x, length, angle):
        dir_x = -math.sin(angle)
        dir_y =  math.cos(angle)
        top_x    = hip_x;             top_y    = hip_y
        bottom_x = top_x + dir_x * length; bottom_y = top_y + dir_y * length

        nx = -dir_y; ny = dir_x
        hw = 8 * 0.65
        poly(color, [
            (top_x + nx*hw, top_y + ny*hw),
            (top_x - nx*hw, top_y - ny*hw),
            (bottom_x - nx*hw, bottom_y - ny*hw),
            (bottom_x + nx*hw, bottom_y + ny*hw),
        ])
        hoof_x = top_x + dir_x * (length - 5)
        hoof_y = top_y + dir_y * (length - 5)
        cos_a = math.cos(angle); sin_a = math.sin(angle)
        hoof_pts = [
            (hoof_x + px*cos_a - py*sin_a, hoof_y + px*sin_a + py*cos_a)
            for px, py in hoof_vertices(
                traits.get("hoof_length", C.HOOF_LENGTH_MAX),
                traits.get("hoof_shape", C.HOOF_SHAPE_TAPERED),
            )
        ]
        poly(C.DARK, hoof_pts)

    draw_world_leg(back_hip_x, back_length, -start_angle)

    _, body, neck, head, ear, muzzle, eye, pupil, nose, mouth = horse_body_geometry(
        torso_length, torso_height
    )
    tail_length = traits.setdefault(
        "tail_length",
        random.uniform(C.TAIL_LENGTH_MIN, C.TAIL_LENGTH_MAX),
    )
    tail_width = traits.setdefault(
        "tail_width",
        random.uniform(C.TAIL_WIDTH_MIN, C.TAIL_WIDTH_MAX),
    )
    tail_anchor = (
        C.MODEL_CENTRE_X - torso_length / 2 + C.TORSO_HIP_INSET,
        C.MODEL_CENTRE_Y - torso_height / 2,
    )
    tail_angle = theta + C.TAIL_START_ANGLE
    tail_direction = (-math.sin(tail_angle), math.cos(tail_angle))
    tail_normal = (math.cos(tail_angle), math.sin(tail_angle))
    tail_tip = (
        tail_anchor[0] + tail_direction[0] * tail_length,
        tail_anchor[1] + tail_direction[1] * tail_length,
    )
    poly(color, (
        (
            tail_anchor[0] - tail_normal[0] * tail_width * 0.175,
            tail_anchor[1] - tail_normal[1] * tail_width * 0.175,
        ),
        (
            tail_anchor[0] + tail_normal[0] * tail_width * 0.175,
            tail_anchor[1] + tail_normal[1] * tail_width * 0.175,
        ),
        (
            tail_tip[0] + tail_normal[0] * tail_width / 2,
            tail_tip[1] + tail_normal[1] * tail_width / 2,
        ),
        (
            tail_tip[0] - tail_normal[0] * tail_width / 2,
            tail_tip[1] - tail_normal[1] * tail_width / 2,
        ),
    ))
    poly(color, body)
    poly(color, neck)
    poly(color, head)
    poly(color, ear)
    poly(color, muzzle)
    pygame.draw.circle(big, C.WHITE, pt(*eye), max(1, int(round(4 * k))))
    pygame.draw.circle(big, C.BLACK, pt(*pupil), max(1, int(round(2 * k))))
    poly(C.BLACK, nose)
    poly(C.WHITE, mouth)

    draw_world_leg(front_hip_x, front_length, start_angle)

    bounds  = big.get_bounding_rect()
    cropped = big.subsurface(bounds).copy()
    width   = max(1, int(round(bounds.width  / ss)))
    height  = max(1, int(round(bounds.height / ss)))
    return pygame.transform.smoothscale(cropped, (width, height))