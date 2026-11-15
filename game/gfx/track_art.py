"""track_art.py — The race track: background, lanes, and the trackside sign.

The overworld copy of the track is a tiny pixel-art building; build_race_track_sprite
draws it, draw_race_track stamps it into the world.
"""

import pygame

from game import constants as C
from game.constants import s
from game.gfx.fonts import get_font


def draw_track(
    screen: pygame.Surface,
    bet_info=None,
    camera_x: float = 0,
) -> None:
    """Draw the race-track background, lanes, start/finish lines."""
    screen.fill(C.GRASS_BG)

    sky_height = C.TRACK_TOP
    if sky_height > 0:
        pygame.draw.rect(screen, C.SKY_BLUE, (0, 0, C.WIDTH, sky_height))

    font       = get_font(s(32), bold=True)
    line_width = max(1, s(2))
    inner_h    = C.LANE_HEIGHT - C.LANE_PAD

    for i in range(C.LANE_COUNT):
        y = C.TRACK_TOP + i * C.LANE_HEIGHT

        pygame.draw.line(screen, C.LINE, (0, y), (C.WIDTH, y), line_width)
        pygame.draw.line(screen, C.LINE, (0, y + inner_h), (C.WIDTH, y + inner_h), line_width)

        label = font.render(str(i + 1), True, C.WHITE)
        screen.blit(label, (s(12), y + s(55)))

    # Starting line
    pygame.draw.line(
        screen, C.WHITE,
        (C.START_LINE_X - int(camera_x), C.TRACK_TOP),
        (C.START_LINE_X - int(camera_x), C.TRACK_TOP + (C.LANE_COUNT - 1) * C.LANE_HEIGHT + inner_h),
        max(1, s(3)),
    )

    # Finish line
    pygame.draw.rect(
        screen, C.WHITE,
        (C.FINISH_X - int(camera_x), C.TRACK_TOP,
         C.FINISH_WIDTH, (C.LANE_COUNT - 1) * C.LANE_HEIGHT + inner_h),
    )

    # Halfway marker
    halfway_x = C.HALFWAY_X - int(camera_x)
    track_bottom = C.TRACK_TOP + (C.LANE_COUNT - 1) * C.LANE_HEIGHT + inner_h
    dash_height = max(4, s(12))
    dash_gap = max(3, s(7))
    for y in range(C.TRACK_TOP, track_bottom, dash_height + dash_gap):
        pygame.draw.line(
            screen,
            C.GOLD,
            (halfway_x, y),
            (halfway_x, min(y + dash_height, track_bottom)),
            max(2, s(3)),
        )

    halfway_font = get_font(s(18), bold=True)
    halfway_label = halfway_font.render("HALFWAY", True, C.GOLD)
    halfway_label_rect = halfway_label.get_rect(
        midbottom=(halfway_x, C.TRACK_TOP - s(4))
    )
    screen.blit(halfway_label, halfway_label_rect)

    # Bet info
    if bet_info is not None:
        bet_font = get_font(s(22), bold=True)
        bet_text = bet_font.render(
            f"Your Bet: Horse {bet_info[0] + 1} (${bet_info[1]})",
            True, C.GOLD,
        )
        screen.blit(bet_text, (s(50), s(10)))


def lane_rect(lane: int) -> pygame.Rect:
    """Return the clickable rectangle for a betting lane."""
    return pygame.Rect(
        C.TRACK_LEFT,
        C.TRACK_TOP + lane * C.LANE_HEIGHT,
        C.TRACK_RIGHT - C.TRACK_LEFT,
        C.LANE_HEIGHT - C.LANE_PAD,
    )


def build_race_track_sprite() -> pygame.Surface:
    """The race track as a small pixel-art building for the overworld."""
    grid = [[None] * C.TRACK_COLS for _ in range(C.TRACK_ROWS)]

    def fill(c0, r0, c1, r1, color):
        for r in range(max(0, r0), min(C.TRACK_ROWS, r1 + 1)):
            for c in range(max(0, c0), min(C.TRACK_COLS, c1 + 1)):
                grid[r][c] = color

    def outline(c0, r0, c1, r1, color):
        for c in range(c0, c1 + 1):
            grid[r0][c] = color
            grid[r1][c] = color
        for r in range(r0, r1 + 1):
            grid[r][c0] = color
            grid[r][c1] = color

    # Title banner
    fill(13,2,52,9, C.TITLE_BG);     outline(13,2,52,9, C.DARK_BROWN)
    # R
    fill(15,4,15,7, C.TITLE_PURPLE); fill(16,4,17,4, C.TITLE_PURPLE)
    fill(17,5,17,5, C.TITLE_PURPLE); fill(16,6,16,6, C.TITLE_PURPLE)
    fill(17,7,17,7, C.TITLE_PURPLE)
    # A
    fill(19,5,19,7, C.TITLE_PURPLE); fill(20,4,20,4, C.TITLE_PURPLE)
    fill(21,5,21,7, C.TITLE_PURPLE); fill(20,6,20,6, C.TITLE_PURPLE)
    # C
    fill(23,4,25,4, C.TITLE_PURPLE); fill(23,5,23,7, C.TITLE_PURPLE)
    fill(24,7,25,7, C.TITLE_PURPLE)
    # E
    fill(27,4,29,4, C.TITLE_PURPLE); fill(27,5,27,7, C.TITLE_PURPLE)
    fill(28,5,28,6, C.TITLE_PURPLE); fill(27,7,29,7, C.TITLE_PURPLE)
    # T
    fill(32,4,34,4, C.TITLE_PURPLE); fill(33,5,33,7, C.TITLE_PURPLE)
    # R
    fill(36,4,36,7, C.TITLE_PURPLE); fill(37,4,38,4, C.TITLE_PURPLE)
    fill(38,5,38,5, C.TITLE_PURPLE); fill(37,6,37,6, C.TITLE_PURPLE)
    fill(38,7,38,7, C.TITLE_PURPLE)
    # A
    fill(40,5,40,7, C.TITLE_PURPLE); fill(41,4,41,4, C.TITLE_PURPLE)
    fill(42,5,42,7, C.TITLE_PURPLE); fill(41,6,41,6, C.TITLE_PURPLE)
    # C
    fill(44,4,46,4, C.TITLE_PURPLE); fill(44,5,44,7, C.TITLE_PURPLE)
    fill(45,7,46,7, C.TITLE_PURPLE)
    # K
    fill(48,4,48,7, C.TITLE_PURPLE)
    grid[5][49] = C.TITLE_PURPLE; grid[6][50] = C.TITLE_PURPLE
    fill(51,4,51,4, C.TITLE_PURPLE); fill(51,7,51,7, C.TITLE_PURPLE)

    # Grandstands
    flag_colors = (C.FLAG_PINK, C.FLAG_GREEN, C.FLAG_PURPLE)
    for i in range(3):
        gx = 18 + i * 10
        fill(gx,12,gx+8,13, C.STAND_LIGHT); outline(gx,12,gx+8,13, C.STAND_DARK)
        fill(gx,14,gx+8,23, C.STAND_GRAY);  outline(gx,14,gx+8,23, C.STAND_DARK)
        for ry in (16, 19, 21):
            for cx in range(gx + 1, gx + 8):
                grid[ry][cx] = C.STAND_DARK
        pole_x = gx + 4
        for py in range(7, 12):
            grid[py][pole_x] = C.STAND_DARK
        fill(pole_x+1,7,pole_x+4,10, flag_colors[i])

    # Oval track
    fill(8,25,57,45,  C.TRACK_GREEN);        outline(8,25,57,45,  C.TRACK_DARK_GREEN)
    fill(13,29,52,41, C.TRACK_ORANGE);       outline(13,29,52,41, C.TRACK_LIGHT_ORANGE)
    fill(32,29,34,36, C.WHITE)

    # Fence
    fill(3,30,9,40,   C.BROWN);              outline(3,30,9,40,   C.DARK_BROWN)
    fill(4,33,8,37,   C.FENCE_INNER)
    for fx in range(4, 9, 2):
        grid[31][fx] = C.DARK_BROWN
        grid[39][fx] = C.DARK_BROWN

    # Gate
    fill(0,27,2,43,   C.STAND_GRAY);         outline(0,27,2,43,   C.STAND_DARK)
    fill(1,30,1,40,   C.WHITE)

    surface = pygame.Surface(
        (C.TRACK_COLS * C.TRACK_CELL, C.TRACK_ROWS * C.TRACK_CELL),
        pygame.SRCALPHA,
    )
    for r in range(C.TRACK_ROWS):
        for c in range(C.TRACK_COLS):
            color = grid[r][c]
            if color is not None:
                pygame.draw.rect(
                    surface, color,
                    (c * C.TRACK_CELL, r * C.TRACK_CELL, C.TRACK_CELL, C.TRACK_CELL),
                )
    return surface


def draw_race_track(screen: pygame.Surface,
                    track_sprite: pygame.Surface,
                    track_rect: pygame.Rect,
                    camera_x: float, camera_y: float) -> None:
    sx, sy = int(track_rect.x - camera_x), int(track_rect.y - camera_y)
    screen.blit(track_sprite, (sx, sy))