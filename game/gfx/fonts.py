"""fonts.py — Cached system fonts.

Fonts are expensive to create, so every size/weight pair is built once.
"""

import pygame

_font_cache: dict = {}


def get_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont("Arial", size, bold=bold)
    return _font_cache[key]