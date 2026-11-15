"""horse_draw.py — Drawing a physics horse (race track, van, farm, shop)."""

import math

import pygame

from game import constants as C
from game.gfx.horse_model import hoof_vertices, horse_body_geometry
from game.physics import PhysicsBody


def model_point(x: float, y: float, angle: float,
                px: float, py: float, size_scale: float = 1.0) -> tuple:
    """Transform a model-space point into world-space for drawing."""
    local_x = (px - C.MODEL_CENTRE_X) * C.SCALE * size_scale
    local_y = (py - C.MODEL_CENTRE_Y) * C.SCALE * size_scale

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    world_x = x + local_x * cos_a - local_y * sin_a
    world_y = y + local_x * sin_a + local_y * cos_a

    return int(world_x), int(world_y)


def draw_horse_body(surface: pygame.Surface, horse, camera_x: float = 0) -> None:
    """Draw the torso, neck, head and details of a RaceHorse."""
    torso = horse.torso
    x     = torso.position.x
    y     = torso.position.y
    angle = torso.angle
    color = horse.color

    def point(px, py):
        world_x, world_y = model_point(
            x, y, angle, px, py, horse.size_scale
        )
        return world_x - int(camera_x), world_y

    def poly(c, points):
        pygame.draw.polygon(
            surface, c,
            [point(px, py) for px, py in points],
        )

    _, body, *_ = horse_body_geometry(
        horse.torso_length, horse.torso_height
    )
    poly(color, body)


def draw_horse_tail(surface: pygame.Surface, horse, camera_x: float = 0) -> None:
    tail = horse.tail
    half_width = tail.width * C.SCALE * horse.size_scale / 2
    half_length = tail.length * C.SCALE * horse.size_scale / 2
    points = [
        tail.body.local_to_world((-half_width * 0.35, -half_length)),
        tail.body.local_to_world((half_width * 0.35, -half_length)),
        tail.body.local_to_world((half_width, half_length)),
        tail.body.local_to_world((-half_width, half_length)),
    ]
    pygame.draw.polygon(
        surface,
        horse.color,
        [(int(point.x - camera_x), int(point.y)) for point in points],
    )


def draw_horse_head(surface: pygame.Surface, horse, camera_x: float = 0) -> None:
    color = horse.color
    head_body = horse.head.body
    geometry = horse_body_geometry(horse.torso_length, horse.torso_height)
    neck, head, ear, muzzle, eye, pupil, nose, mouth = geometry[2:]

    def point(px: float, py: float) -> tuple[int, int]:
        world = head_body.local_to_world((
            (px - horse.head.center_x) * C.SCALE * horse.size_scale,
            (py - horse.head.center_y) * C.SCALE * horse.size_scale,
        ))
        return int(world.x - camera_x), int(world.y)

    def poly(draw_color, points) -> None:
        pygame.draw.polygon(surface, draw_color, [point(px, py) for px, py in points])

    poly(color, neck)
    poly(color, head)
    poly(color, ear)
    poly(color, muzzle)
    pygame.draw.circle(
        surface, C.WHITE, point(*eye),
        max(1, int(4 * C.SCALE * horse.size_scale)),
    )
    pygame.draw.circle(
        surface, C.BLACK, point(*pupil),
        max(1, int(2 * C.SCALE * horse.size_scale)),
    )
    poly(C.BLACK, nose)
    poly(C.WHITE, mouth)


def draw_leg(surface: pygame.Surface,
             leg: PhysicsBody,
             color: tuple,
             leg_length: float,
             hoof_length: float,
             hoof_shape: str,
             camera_x: float = 0,
             size_scale: float = 1.0) -> None:
    """Draw one physics leg as a thick segment with a hoof."""
    top    = leg.local_to_world((0, -leg_length / 2))
    bottom = leg.local_to_world((0,  leg_length / 2))

    dx = bottom.x - top.x
    dy = bottom.y - top.y
    length = max(1, math.hypot(dx, dy))

    nx = -dy / length
    ny =  dx / length

    hw = C.LEG_DRAW_WIDTH * size_scale / 2
    pts = [
        (top.x    + nx * hw - camera_x, top.y    + ny * hw),
        (top.x    - nx * hw - camera_x, top.y    - ny * hw),
        (bottom.x - nx * hw - camera_x, bottom.y - ny * hw),
        (bottom.x + nx * hw - camera_x, bottom.y + ny * hw),
    ]
    pygame.draw.polygon(surface, color, [(int(px), int(py)) for px, py in pts])

    # Hoof
    hoof_center = leg.local_to_world(
        (0, leg_length / 2 - 2 * C.U * size_scale)
    )
    cos_a = math.cos(leg.angle)
    sin_a = math.sin(leg.angle)

    hoof_pts = []
    for model_x, model_y in hoof_vertices(hoof_length, hoof_shape):
        px = model_x * C.SCALE * size_scale
        py = model_y * C.SCALE * size_scale
        hoof_pts.append((
            int(hoof_center.x + px * cos_a - py * sin_a - camera_x),
            int(hoof_center.y + px * sin_a + py * cos_a),
        ))
    pygame.draw.polygon(surface, C.DARK, hoof_pts)


def draw_horses(
    surface: pygame.Surface,
    horses: list,
    camera_x: float = 0,
) -> None:
    """Draw all RaceHorse objects in *horses*."""
    for horse in horses:
        horse.draw(surface, camera_x)