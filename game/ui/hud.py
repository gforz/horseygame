"""hud.py — Top-left HUD: money box with the lasso counter button below it."""

import pygame

from game import constants as C
from game import daytime
from game import state
from game.gfx.fonts import get_font
from game.items import get_pixel_lasso_sprite

WHITE = (255, 255, 255)
BOX_BORDER = (190, 190, 190)
MONEY_GREEN = (30, 160, 50)
BUTTON_FILL = (246, 165, 60)
BUTTON_BORDER = (214, 124, 30)
COUNT_BLUE = (30, 60, 210)

# RGB multipliers tint and darken the scene without covering UI drawn afterward.
STAGE_LIGHTING = {
    "Morning": (235, 220, 190),
    "Noon": (190, 210, 245),
    "Night": (70, 80, 120),
}


def _draw_lasso_button(screen: pygame.Surface, x: int, y: int) -> None:
    """Orange rounded button with a lasso icon and the owned count."""
    size = C.s(48)
    rect = pygame.Rect(x, y, size, size)
    pygame.draw.rect(screen, BUTTON_FILL, rect, border_radius=C.s(8))
    pygame.draw.rect(screen, BUTTON_BORDER, rect, max(2, C.s(3)), border_radius=C.s(8))

    sprite = get_pixel_lasso_sprite(1)
    target_h = int(size * 0.72)
    target_w = max(1, int(sprite.get_width() * target_h / sprite.get_height()))
    icon = pygame.transform.scale(sprite, (target_w, target_h))
    screen.blit(icon, icon.get_rect(center=(rect.centerx - C.s(2), rect.centery - C.s(2))))

    count = get_font(C.s(18), bold=True).render(str(state.lasso_count), True, COUNT_BLUE)
    screen.blit(count, count.get_rect(bottomright=(rect.right - C.s(5), rect.bottom - C.s(2))))


def draw_time_lighting(screen: pygame.Surface) -> None:
    """Apply the current stage's ambient color to the scene."""
    multiplier = STAGE_LIGHTING.get(daytime.name())
    if multiplier is not None:
        screen.fill(multiplier, special_flags=pygame.BLEND_RGB_MULT)


def draw_hud(screen: pygame.Surface, money_font=None, show_lasso: bool = True) -> None:
    """Draw the money box and optional lasso button."""
    if money_font is None:
        money_font = get_font(C.s(28), bold=True)

    margin = C.s(8)
    text = money_font.render(f"${state.player_money}", True, MONEY_GREEN)
    box = pygame.Rect(
        margin,
        margin,
        text.get_width() + C.s(10) * 2,
        text.get_height() + C.s(4) * 2,
    )
    pygame.draw.rect(screen, WHITE, box, border_radius=C.s(8))
    pygame.draw.rect(screen, BOX_BORDER, box, max(1, C.s(2)), border_radius=C.s(8))
    screen.blit(text, text.get_rect(center=box.center))

    if show_lasso:
        _draw_lasso_button(screen, box.left, box.bottom + C.s(8))