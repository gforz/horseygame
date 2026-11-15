"""shop_art.py — Lasso-Mart's room: geometry, walls, counter, price board, van.

All the shop's layout maths lives in Room so drawing and hit-testing always
agree; the draw_* helpers each paint one part of the scene.
"""

import pygame

from game import constants as C
from game.constants import HUB, VAN_BED, VAN_BORDER, VAN_FILL, WHEEL
from game.gfx.fonts import get_font
from game.items import (
    LASSO_ANCHOR,
    LASSO_H,
    LASSO_W,
    get_pixel_lasso_sprite,
)

# Room colours
WALL_BG = (105, 68, 28)
FLOOR_BG = (75, 48, 18)
PANEL_BG = (26, 101, 10)
PANEL_BORDER = (18, 70, 8)
HOVER_BG = (42, 142, 28)
TEXT_WHITE = (255, 255, 255)
GOLD = (255, 215, 0)

TITLE_OUTLINE = (185, 60, 215)
TITLE_INNER = (95, 30, 105)

# One lasso costs this much; hay is 5.
LASSO_PRICE = 65
HAY_PRICE = 5


class Room:
    """Shop geometry, in screen pixels."""

    def __init__(self, width: int, height: int) -> None:
        self.w = width
        self.h = height
        self.floor_y = int(height * 0.48)

        # Lasso pegboard on the back wall
        pb_w = int(width * 0.13)
        pb_h = int(height * 0.24)
        pb_x = int(width * 0.28)
        pb_y = int(height * 0.14)
        self.lasso_board_rect = pygame.Rect(pb_x, pb_y, pb_w, pb_h)
        self.lasso_pixel = max(2, round(pb_w * 0.012))
        self.peg_coords = [
            (pb_x + int(pb_w * 0.30), pb_y + int(pb_h * 0.14)),
            (pb_x + int(pb_w * 0.72), pb_y + int(pb_h * 0.14)),
            (pb_x + int(pb_w * 0.30), pb_y + int(pb_h * 0.58)),
            (pb_x + int(pb_w * 0.74), pb_y + int(pb_h * 0.66)),
        ]
        # Clickable area of each lasso hanging on the pegboard
        self.lasso_hit_rects = [
            pygame.Rect(
                px - LASSO_ANCHOR[0] * self.lasso_pixel,
                py - LASSO_ANCHOR[1] * self.lasso_pixel,
                LASSO_W * self.lasso_pixel,
                LASSO_H * self.lasso_pixel,
            )
            for px, py in self.peg_coords
        ]

        # Price list board on right wall
        board_w = int(width * 0.18)
        board_h = int(height * 0.24)
        board_x = int(width * 0.63)
        board_y = int(height * 0.14)
        self.board_rect = pygame.Rect(board_x, board_y, board_w, board_h)

        row_h = int(board_h * 0.38)
        row_pad = int(board_h * 0.08)
        self.hay_row_rect = pygame.Rect(board_x + 10, board_y + row_pad, board_w - 20, row_h)
        self.lasso_row_rect = pygame.Rect(
            board_x + 10, board_y + row_pad + row_h + int(board_h * 0.08), board_w - 20, row_h
        )

        # 3D counter sitting on the floor
        fx1, fy_base = int(width * 0.20), int(height * 0.82)
        fx2 = int(width * 0.35)
        bx1, by_base = int(width * 0.40), int(height * 0.58)
        bx2 = int(width * 0.53)

        ch_front = int(height * 0.16)
        ch_back = int(height * 0.12)

        fl_top = (fx1, fy_base - ch_front)
        fr_top = (fx2, fy_base - ch_front)
        bl_top = (bx1, by_base - ch_back)
        br_top = (bx2, by_base - ch_back)

        fl_base = (fx1, fy_base)
        fr_base = (fx2, fy_base)
        br_base = (bx2, by_base)

        self.counter_side_pts = [fr_top, br_top, br_base, fr_base]
        self.counter_front_pts = [fl_top, fr_top, fr_base, fl_base]
        self.counter_top_pts = [fl_top, fr_top, br_top, bl_top]
        self.counter_fl_top = fl_top
        self.counter_fr_top = fr_top
        self.counter_bl_top = bl_top
        self.counter_br_top = br_top

        # Horse trailer on the bottom right
        van_w = int(width * 0.42)
        van_h = int(height * 0.40)
        van_x = int(width * 0.56)
        van_y = int(height * 0.54)

        self.van_rect = pygame.Rect(van_x, van_y, van_w, van_h)
        border_t = max(6, int(van_h * (8 / 142)))
        self.van_fill_rect = pygame.Rect(
            van_x + border_t, van_y + border_t, van_w - border_t * 2, van_h - border_t * 2
        )
        self.van_drop_rect = self.van_rect.inflate(20, 20)

    def sheaf_home(self, u: float, v: float, hay_h: int) -> tuple[int, int]:
        """Where a counter sheaf sits, as a fraction across the counter top."""
        front_x = self.counter_fl_top[0] + (self.counter_fr_top[0] - self.counter_fl_top[0]) * u
        front_y = self.counter_fl_top[1] + (self.counter_fr_top[1] - self.counter_fl_top[1]) * u
        back_x = self.counter_bl_top[0] + (self.counter_br_top[0] - self.counter_bl_top[0]) * u
        back_y = self.counter_bl_top[1] + (self.counter_br_top[1] - self.counter_bl_top[1]) * u
        return (
            int(front_x + (back_x - front_x) * v),
            int(front_y + (back_y - front_y) * v) - int(hay_h * 0.3),
        )


def draw_room(screen: pygame.Surface, room: Room) -> None:
    """Wall, floor, planks and baseboard."""
    screen.fill(WALL_BG)
    pygame.draw.rect(screen, FLOOR_BG, (0, room.floor_y, room.w, room.h - room.floor_y))

    plank_w = max(18, int(room.w * 0.026))
    for px in range(0, room.w, plank_w):
        pygame.draw.line(screen, (70, 44, 16), (px, 0), (px, room.floor_y), 1)
        pygame.draw.line(screen, (135, 90, 40), (px + 1, 0), (px + 1, room.floor_y), 1)

    baseboard_h = max(6, int(room.h * 0.012))
    pygame.draw.rect(
        screen, (120, 78, 30), (0, room.floor_y - baseboard_h // 2, room.w, baseboard_h)
    )
    pygame.draw.line(
        screen,
        (150, 100, 42),
        (0, room.floor_y - baseboard_h // 2),
        (room.w, room.floor_y - baseboard_h // 2),
        2,
    )
    pygame.draw.line(
        screen,
        (55, 35, 12),
        (0, room.floor_y + baseboard_h // 2),
        (room.w, room.floor_y + baseboard_h // 2),
        2,
    )


def draw_title(screen: pygame.Surface, room: Room) -> None:
    """"Horse-Mart" in retro purple outline style at the top centre."""
    title_font = get_font(C.s(42), bold=True)
    title_cy = C.s(38)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
        t_surf = title_font.render("Horse-Mart", True, TITLE_OUTLINE)
        screen.blit(t_surf, t_surf.get_rect(center=(room.w // 2 + dx, title_cy + dy)))
    t_in = title_font.render("Horse-Mart", True, TITLE_INNER)
    screen.blit(t_in, t_in.get_rect(center=(room.w // 2, title_cy)))


def draw_lasso_board(screen: pygame.Surface, room: Room, lasso_pixel: int,
                     lasso_left: int, hover: bool) -> None:
    """Pegboard, pegs and one lasso per item left in stock."""
    pygame.draw.rect(screen, (142, 248, 145), room.lasso_board_rect)
    if hover:
        pygame.draw.rect(screen, (200, 255, 200), room.lasso_board_rect,
                         max(3, int(room.w * 0.004)))
    else:
        pygame.draw.rect(screen, (100, 205, 105), room.lasso_board_rect,
                         max(2, int(room.w * 0.003)))

    # Peg crosses (+)
    for px, py in room.peg_coords:
        arm = max(2, int(room.lasso_board_rect.width * 0.05))
        pygame.draw.line(screen, (120, 125, 125), (px - arm, py), (px + arm, py), 2)
        pygame.draw.line(screen, (120, 125, 125), (px, py - arm), (px, py + arm), 2)

    for index, (px, py) in enumerate(room.peg_coords):
        if index >= lasso_left:
            continue
        anchor_x, anchor_y = LASSO_ANCHOR
        sprite = get_pixel_lasso_sprite(lasso_pixel)
        screen.blit(
            sprite,
            (px - anchor_x * max(1, lasso_pixel), py - anchor_y * max(1, lasso_pixel)),
        )


def draw_price_board(screen: pygame.Surface, room: Room, lasso_left: int) -> None:
    """Green board listing hay and lasso prices."""
    pygame.draw.rect(screen, PANEL_BG, room.board_rect, border_radius=6)
    pygame.draw.rect(screen, PANEL_BORDER, room.board_rect, 3, border_radius=6)

    item_font = get_font(C.s(24), bold=True)
    hay_text = item_font.render(f"Hay ${HAY_PRICE}", True, TEXT_WHITE)
    if lasso_left > 0:
        lasso_text = item_font.render(f"Lasso ${LASSO_PRICE}", True, TEXT_WHITE)
    else:
        lasso_text = item_font.render("Sold Out", True, (240, 150, 150))

    screen.blit(hay_text, hay_text.get_rect(center=room.hay_row_rect.center))
    screen.blit(lasso_text, lasso_text.get_rect(center=room.lasso_row_rect.center))


def draw_counter(screen: pygame.Surface, room: Room) -> None:
    """Angled wooden desk in 3D perspective."""
    pygame.draw.polygon(screen, (85, 48, 16), room.counter_side_pts)
    pygame.draw.polygon(screen, (115, 65, 22), room.counter_side_pts, 2)

    pygame.draw.polygon(screen, (125, 70, 25), room.counter_front_pts)
    pygame.draw.polygon(screen, (165, 95, 35), room.counter_front_pts, 2)

    pygame.draw.polygon(screen, (145, 85, 30), room.counter_top_pts)
    pygame.draw.polygon(screen, (190, 115, 45), room.counter_top_pts, 2)


def draw_van(screen: pygame.Surface, room: Room, highlight: bool = False) -> None:
    """The trailer the player drops hay into."""
    van_w, van_h = room.van_rect.width, room.van_rect.height
    van_x, van_y = room.van_rect.topleft

    # Undercarriage bed between wheels
    bed_w = int(van_w * (130 / 358))
    bed_h = int(van_h * (32 / 142))
    bed_x = van_x + int(van_w * ((445 - 372) / 358))
    bed_y = van_y + van_h - int(bed_h * 0.4)
    pygame.draw.rect(screen, VAN_BED, (bed_x, bed_y, bed_w, bed_h))

    # Body
    pygame.draw.rect(screen, (255, 230, 80) if highlight else VAN_BORDER, room.van_rect)
    pygame.draw.rect(screen, VAN_FILL, room.van_fill_rect)

    # Wheels
    wheel_r = int(van_h * (22 / 142))
    hub_r = max(2, int(van_h * (7 / 142)))
    for frac in [(475 - 372) / 358, (535 - 372) / 358]:
        cx = van_x + int(van_w * frac)
        cy = van_y + van_h + int(wheel_r * 0.15)
        pygame.draw.circle(screen, WHEEL, (cx, cy), wheel_r)
        pygame.draw.circle(screen, HUB, (cx, cy), hub_r)


def draw_hay_shadow(screen: pygame.Surface, center_x: int, center_y: int,
                    hay_w: int, hay_h: int, extra: int = 6) -> None:
    """Soft ellipse under a dragged sheaf."""
    shadow_w, shadow_h = int(hay_w * 1.1), int(hay_h * 0.3)
    shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), (0, 0, shadow_w, shadow_h))
    screen.blit(
        shadow_surf,
        (int(center_x - shadow_w // 2), int(center_y + hay_h // 2 + extra)),
    )


def draw_drop_prompt(screen: pygame.Surface, room: Room, over_van: bool) -> None:
    """"Drop Hay Here!" while dragging a sheaf over the van."""
    prompt_font = get_font(C.s(20), bold=True)
    prompt_surf = prompt_font.render(
        "Drop Hay Here!", True, (40, 160, 50) if over_van else (120, 170, 210)
    )
    screen.blit(
        prompt_surf,
        prompt_surf.get_rect(
            center=(room.van_rect.centerx, room.van_rect.y + int(room.van_rect.height * 0.80))
        ),
    )