"""iris.py — Iris wipe: the screen closes to a black dot, holds, then opens again."""

import math

import pygame

CLOSE_TIME = 0.8   # seconds for the circle to close
HOLD_TIME = 0.5    # seconds fully black (the change happens here)
OPEN_TIME = 0.8    # seconds for the circle to open again


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


class Iris:
    """Draw it on top of the finished frame every frame while it is active."""

    def __init__(self) -> None:
        self.phase = None        # None | "close" | "hold" | "open"
        self.t = 0.0
        self.center = (0, 0)
        self.on_dark = None      # called once, when the screen is fully black
        self._overlay = None

    @property
    def active(self) -> bool:
        return self.phase is not None

    def start(self, center: tuple, on_dark=None) -> None:
        if self.active:
            return
        self.phase = "close"
        self.t = 0.0
        self.center = center
        self.on_dark = on_dark

    def start_open(self, center: tuple) -> None:
        """Begin opening from a fully black screen."""
        if self.active:
            return
        self.phase = "open"
        self.t = 0.0
        self.center = center
        self.on_dark = None

    def update(self, dt: float) -> None:
        if self.phase is None:
            return
        self.t += dt
        if self.phase == "close" and self.t >= CLOSE_TIME:
            self.phase, self.t = "hold", 0.0
            if self.on_dark is not None:
                self.on_dark()
        elif self.phase == "hold" and self.t >= HOLD_TIME:
            self.phase, self.t = "open", 0.0
        elif self.phase == "open" and self.t >= OPEN_TIME:
            self.phase = None

    def draw(self, screen: pygame.Surface) -> None:
        if self.phase is None:
            return

        w, h = screen.get_size()
        cx, cy = self.center
        max_r = math.hypot(max(cx, w - cx), max(cy, h - cy)) + 2

        if self.phase == "close":
            radius = max_r * (1.0 - _ease(min(1.0, self.t / CLOSE_TIME)))
        elif self.phase == "hold":
            radius = 0.0
        else:
            radius = max_r * _ease(min(1.0, self.t / OPEN_TIME))

        if radius <= 1:
            screen.fill((0, 0, 0))
            return

        if self._overlay is None or self._overlay.get_size() != (w, h):
            self._overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, 255))
        pygame.draw.circle(self._overlay, (0, 0, 0, 0), (int(cx), int(cy)), int(radius))
        screen.blit(self._overlay, (0, 0))