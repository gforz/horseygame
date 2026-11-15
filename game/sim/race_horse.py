"""race_horse.py — A horse that walks itself along the race track."""

import pygame

from game import constants as C
from game.gfx.horse_draw import (
    draw_horse_body,
    draw_horse_head,
    draw_horse_tail,
    draw_leg,
)
from game.physics import PhysicsBody


class RaceHorse:
    """
    A horse competing on the race track.
    Owns a Box2D torso body and a list of two Leg objects.
    """

    def __init__(
        self,
        lane: int,
        torso: PhysicsBody,
        color: tuple,
        legs: list,        # list[Leg]
        leg_lengths: list,  # list[float]
        start_angle: float,
        head,
        tail,
        torso_length: float,
        torso_height: float,
        hoof_length: float,
        hoof_shape: str,
        size_scale: float = 1.0,
        name: str = "",
    ):
        self.lane        = lane
        self.torso       = torso
        self.color       = color
        self.legs        = legs
        self.leg_lengths = leg_lengths
        self.start_angle = start_angle
        self.head = head
        self.tail = tail
        self.torso_length = torso_length
        self.torso_height = torso_height
        self.hoof_length = hoof_length
        self.hoof_shape = hoof_shape
        self.size_scale = size_scale
        self.name = name

    # ------------------------------------------------------------------
    def rect(self) -> pygame.Rect:
        """Bounding rectangle used for collision / finish-line detection."""
        x = self.torso.position.x - C.MODEL_CENTRE_X * C.SCALE * self.size_scale
        y = self.torso.position.y - C.MODEL_CENTRE_Y * C.SCALE * self.size_scale
        body_left = C.MODEL_CENTRE_X - self.torso_length / 2
        body_right = C.MODEL_CENTRE_X + self.torso_length / 2
        body_top = C.MODEL_CENTRE_Y - self.torso_height / 2
        body_bottom = C.MODEL_CENTRE_Y + self.torso_height / 2
        horse_left = body_left - (126 - C.HORSE_LEFT)
        horse_right = body_right + (C.HORSE_RIGHT - 386)
        horse_top = body_top + (C.HORSE_TOP - 222)
        horse_bottom = body_bottom + (C.HORSE_BOTTOM - 355)
        extra_height = max(self.leg_lengths) - (
            C.DEFAULT_LEG_LENGTH * C.SCALE * self.size_scale
        )

        body_rect = pygame.Rect(
            int(x + horse_left * C.SCALE * self.size_scale),
            int(y + horse_top * C.SCALE * self.size_scale),
            int((horse_right - horse_left) * C.SCALE * self.size_scale),
            int((horse_bottom - horse_top) * C.SCALE * self.size_scale + extra_height),
        )
        return body_rect.union(self.head.rect()).union(self.tail.rect())

    def update(self, dt: float, is_dragged: bool) -> None:
        """Step the leg FSMs; skip if the horse is currently being dragged."""
        if is_dragged:
            self.head.stop()
            self.tail.stop()
            for leg in self.legs:
                leg.stop()
            return

        self.head.update()
        self.tail.update()
        for leg_index, leg in enumerate(self.legs):
            leg.update(dt, self.torso, leg_index)

    def draw(self, surface: pygame.Surface, camera_x: float = 0) -> None:
        """Draw legs, body and head onto *surface*."""
        # Back leg first (drawn behind body)
        draw_leg(
            surface, self.legs[0].body, self.color, self.leg_lengths[0],
            self.hoof_length, self.hoof_shape, camera_x, self.size_scale,
        )
        draw_horse_tail(surface, self, camera_x)
        draw_horse_body(surface, self, camera_x)
        draw_horse_head(surface, self, camera_x)
        # Front leg on top
        draw_leg(
            surface, self.legs[1].body, self.color, self.leg_lengths[1],
            self.hoof_length, self.hoof_shape, camera_x, self.size_scale,
        )