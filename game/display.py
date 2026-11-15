"""display.py — The single game window.

Scenes draw on the window returned by get_screen(); if a scene changed the
display mode, the next call restores the game's own size and flags.
"""

from pathlib import Path

import pygame

from game import constants as C

DISPLAY_FLAGS = pygame.SCALED | pygame.RESIZABLE
CURSOR_PATH = Path(__file__).parent / "ui" / "mouse_cursor.png"
CURSOR_SCALE = 1.1
_game_cursor: pygame.cursors.Cursor | None = None


def _get_game_cursor() -> pygame.cursors.Cursor:
    global _game_cursor
    if _game_cursor is None:
        image = pygame.image.load(str(CURSOR_PATH)).convert_alpha()
        size = tuple(round(dimension * CURSOR_SCALE) for dimension in image.get_size())
        image = pygame.transform.scale(image, size)
        _game_cursor = pygame.cursors.Cursor((1, 0), image)
    return _game_cursor


def set_game_cursor() -> None:
    """Use the supplied arrow cursor when the display driver supports cursors."""
    if pygame.display.get_driver() != "dummy":
        pygame.mouse.set_cursor(_get_game_cursor())


def set_hand_cursor() -> None:
    """Use the system hand cursor for interactive shop items."""
    if pygame.display.get_driver() != "dummy":
        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)


def get_screen() -> pygame.Surface:
    """Return the game window, creating it only if it doesn't exist yet."""
    surf = pygame.display.get_surface()
    if surf is None or surf.get_size() != (C.WIDTH, C.HEIGHT):
        surf = pygame.display.set_mode((C.WIDTH, C.HEIGHT), DISPLAY_FLAGS)
    set_game_cursor()
    return surf