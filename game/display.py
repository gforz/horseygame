"""display.py — The single game window.

Scenes draw on the window returned by get_screen(); if a scene changed the
display mode, the next call restores the game's own size and flags.
"""

import pygame

from game import constants as C

DISPLAY_FLAGS = pygame.SCALED | pygame.RESIZABLE
CURSOR_SCALE = 2
_game_cursor: pygame.cursors.Cursor | None = None


def _get_game_cursor() -> pygame.cursors.Cursor:
    global _game_cursor
    if _game_cursor is None:
        (width, height), hotspot, xor_mask, mask = pygame.cursors.arrow.data
        image = pygame.Surface((width, height), pygame.SRCALPHA)
        bytes_per_row = (width + 7) // 8
        for y in range(height):
            for x in range(width):
                index = y * bytes_per_row + x // 8
                bit = 1 << (7 - x % 8)
                if mask[index] & bit:
                    color = (0, 0, 0) if xor_mask[index] & bit else (255, 255, 255)
                    image.set_at((x, y), color)
        size = tuple(round(dimension * CURSOR_SCALE) for dimension in image.get_size())
        image = pygame.transform.scale(image, size)
        scaled_hotspot = tuple(round(coordinate * CURSOR_SCALE) for coordinate in hotspot)
        _game_cursor = pygame.cursors.Cursor(scaled_hotspot, image)
    return _game_cursor


def set_game_cursor() -> None:
    """Use an enlarged version of Pygame's default arrow cursor."""
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