"""app.py — Wires the entry point to the first scene."""

import pygame

from game.scenes.world import run_world


def run() -> None:
    """Initialise pygame, play from the overworld, then shut down."""
    pygame.init()

    # Screen-dependent constants are read when the game modules are imported.
    run_world()
    pygame.quit()