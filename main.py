"""
main.py — Entry point for the Horsey Game.
"""
import pygame


def main() -> None:
    pygame.init()

    # Screen-dependent constants are set when the game modules are imported.
    from world import run_world

    run_world()
    pygame.quit()


if __name__ == "__main__":
    main()
