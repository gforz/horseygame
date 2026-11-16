"""app.py — Wires the entry point to the first scene."""

import pygame


def run() -> None:
    """Initialise pygame, run playthroughs, then shut down."""
    pygame.init()

    # Import scenes after pygame starts so screen-dependent constants can use
    # the user's desktop resolution.
    from game import daytime, state
    from game.items import HAY
    from game.scenes.shop import reset_shop
    from game.scenes.world import run_world

    open_with_iris = False
    while run_world(open_with_iris):
        state.reset()
        daytime.reset()
        HAY.clear()
        reset_shop()
        open_with_iris = True

    pygame.quit()